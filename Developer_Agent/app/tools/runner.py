"""Runs a stack's allowlisted commands inside one project folder.

LocalRunner runs them on this machine. DockerRunner runs each one in a throw-away container with only
the project folder mounted. Both take their commands from the stack profile, resolve its tokens, and
return the same CommandResult, so nothing else in the service cares which one is used.
"""

import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import (
    CACHE_DIR, DOCKER_CPUS, DOCKER_MEMORY, IMPORT_TIMEOUT_SECONDS, INSTALL_TIMEOUT_SECONDS, RUNNER_MODE,
    TEST_TIMEOUT_SECONDS,
)

# Per-command time limits in seconds. Installing is the slow one (many packages, cold cache).
# Override with INSTALL_TIMEOUT_SECONDS / IMPORT_TIMEOUT_SECONDS / TEST_TIMEOUT_SECONDS.
TIMEOUTS = {"install": INSTALL_TIMEOUT_SECONDS, "check_imports": IMPORT_TIMEOUT_SECONDS, "test": TEST_TIMEOUT_SECONDS}
SETUP_TIMEOUT = 120
DEFAULT_TIMEOUT = 180

# Child processes get only these variables. The service's own environment holds LLM provider keys and the
# service key, and AI-written code (and its tests) must never be able to read them.
SAFE_ENV_NAMES = (
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR",
    "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
    "LANG", "LC_ALL", "TZ", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_CERT",
    "NPM_CONFIG_REGISTRY",
)


def safe_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {name: os.environ[name] for name in SAFE_ENV_NAMES if name in os.environ}
    env.setdefault("PYTHONUTF8", "1")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


@dataclass
class CommandResult:
    name: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def summary(self, max_chars: int = 3000) -> str:
        """Short text to show a human or feed back to the configured LLM."""
        text = (self.stdout + "\n" + self.stderr).strip()
        return text[-max_chars:]  # keep the END, where errors usually are


def _text(value) -> str:
    """subprocess hands back bytes (or None) in TimeoutExpired even when text=True was used."""
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


class AppHandle:
    """A started app: can be asked whether it is alive, for its log, and be stopped."""

    def alive(self) -> bool: raise NotImplementedError
    def log_tail(self, max_chars: int = 3000) -> str: raise NotImplementedError
    def stop(self) -> None: raise NotImplementedError


class LocalAppHandle(AppHandle):
    def __init__(self, process: subprocess.Popen, log_path: Path):
        self.process, self.log_path = process, log_path

    def alive(self) -> bool:
        return self.process.poll() is None

    def log_tail(self, max_chars: int = 3000) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
        except OSError:
            return ""

    def stop(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            if sys.platform == "win32":  # kill the whole process tree (npm/uvicorn start children)
                subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"], capture_output=True)
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()


class DockerAppHandle(AppHandle):
    def __init__(self, name: str, database_name: str | None = None, network_name: str | None = None):
        self.name = name
        self.database_name = database_name
        self.network_name = network_name

    def alive(self) -> bool:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.name], capture_output=True, text=True)
        return result.returncode == 0 and result.stdout.strip() == "true"

    def log_tail(self, max_chars: int = 3000) -> str:
        result = subprocess.run(["docker", "logs", "--tail", "200", self.name], capture_output=True, text=True)
        return (result.stdout + result.stderr)[-max_chars:]

    def stop(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        if self.database_name:
            subprocess.run(["docker", "rm", "-f", self.database_name], capture_output=True)
        if self.network_name:
            subprocess.run(["docker", "network", "rm", self.network_name], capture_output=True)
        # The named data volume is deliberately retained between preview runs.


class BaseRunner:
    def __init__(self, root: Path, stack=None):
        from app.stacks import get_stack
        self.root = Path(root)
        self.stack = stack or get_stack(None)

    # --- pieces the two runners fill in differently -------------------------------------------
    def tokens(self, port: int | None = None) -> dict[str, str]:
        raise NotImplementedError

    def _execute(self, name: str, command: list[str], timeout: int, env: dict[str, str] | None = None) -> CommandResult:
        raise NotImplementedError

    def start_app(self, port: int, log_path: Path | None = None, env: dict[str, str] | None = None) -> AppHandle:
        raise NotImplementedError

    # --- shared ----------------------------------------------------------------------------------
    def _fill(self, template: list[str], port: int | None = None) -> list[str]:
        tokens = self.tokens(port)
        return [part.format(**tokens) if "{" in part else part for part in template]

    def _commands(self) -> dict[str, list[str]]:
        """The allowlist: name -> real command."""
        return {name: self._fill(template) for name, template in self.stack.commands.items()}

    @property
    def venv_dir(self) -> Path:
        return self.root / ".venv"

    def env_ready(self) -> bool:
        return not self.stack.needs_env or (self.root / self.stack.needs_env).exists()

    def setup(self) -> CommandResult | None:
        """Create the project's own environment, replacing an invalid Python venv only."""
        if not self.stack.setup or self.env_ready():
            return None
        if self.stack.needs_env == ".venv":
            # A directory alone is not proof of a usable virtual environment. In
            # particular, Windows Scripts/python.exe cannot run in a Linux container.
            if self.venv_dir.is_symlink() or self.venv_dir.is_file():
                self.venv_dir.unlink(missing_ok=True)
            elif self.venv_dir.exists():
                shutil.rmtree(self.venv_dir)
        return self._execute("setup", self._fill(self.stack.setup), SETUP_TIMEOUT)

    def prepare_environment(self) -> CommandResult | None:
        """Ensure the runtime environment and its dependencies are usable before preview/QA."""
        if not self.stack.needs_env:
            return None
        created = self.setup()
        if created is not None and not created.ok:
            return created
        if "install" not in self.stack.commands:
            return None
        from app.tools import deps
        if deps.unchanged(self.root, self.stack):
            return None
        installed = self.run("install")
        if installed.ok:
            deps.record(self.root, self.stack)
        else:
            deps.forget(self.root, self.stack)
        return installed

    def run(self, name: str, timeout: int | None = None, env: dict[str, str] | None = None) -> CommandResult:
        if name == "create_venv" and self.stack.setup:   # name kept for older callers
            return self._execute(name, self._fill(self.stack.setup), SETUP_TIMEOUT, env)
        commands = self._commands()
        if name not in commands:
            raise ValueError(f"Command not allowed: {name!r}")
        return self._execute(name, commands[name], timeout or TIMEOUTS.get(name, DEFAULT_TIMEOUT), env)


class LocalRunner(BaseRunner):
    """Runs commands on this machine, with a scrubbed environment."""

    def _venv_python(self) -> str:
        # Windows uses Scripts\python.exe, Mac/Linux use bin/python
        return str(self.venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))

    def env_ready(self) -> bool:
        if not self.stack.needs_env:
            return True
        if self.stack.needs_env == ".venv":
            return Path(self._venv_python()).is_file()
        return (self.root / self.stack.needs_env).is_dir()

    def tokens(self, port: int | None = None) -> dict[str, str]:
        return {
            "py": self._venv_python(),
            "host_python": sys.executable,
            "node": shutil.which("node") or "node",
            "npm": shutil.which("npm") or "npm",   # resolves npm.cmd on Windows
            "host": "127.0.0.1",
            "port": str(port or ""),
        }

    def _execute(self, name: str, command: list[str], timeout: int, env: dict[str, str] | None = None) -> CommandResult:
        try:
            result = subprocess.run(
                command, cwd=self.root, env=safe_env(self.stack.check_env), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout,
            )
            return CommandResult(name, result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired as exc:
            # Keep what the command printed so far: it usually shows what was taking so long.
            return CommandResult(name, -1, _text(exc.stdout), f"{_text(exc.stderr)}\nTimed out after {timeout}s")
        except FileNotFoundError as exc:
            return CommandResult(name, -1, "", f"Executable not found: {exc}")

    def start_app(self, port: int, log_path: Path | None = None, env: dict[str, str] | None = None) -> AppHandle:
        command = self._fill(self.stack.start, port)
        log_path = log_path or (self.root.parent / f".{self.root.name}.app.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = open(log_path, "wb")
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {"start_new_session": True}
        process = subprocess.Popen(
            command, cwd=self.root, env=safe_env({**self.stack.check_env, **(env or {}), "PORT": str(port), "HOST": "127.0.0.1"}),
            stdout=log, stderr=subprocess.STDOUT, **options,
        )
        log.close()
        return LocalAppHandle(process, log_path)


class DockerRunner(BaseRunner):
    """Runs each command in a throw-away container. Needs Docker Desktop (or an engine) to be running."""

    def tokens(self, port: int | None = None) -> dict[str, str]:
        return {"py": ".venv/bin/python", "host_python": "python", "node": "node", "npm": "npm",
                "host": "0.0.0.0", "port": str(port or "")}   # 0.0.0.0 inside; only published on 127.0.0.1

    def env_ready(self) -> bool:
        if not self.stack.needs_env:
            return True
        if self.stack.needs_env != ".venv":
            return (self.root / self.stack.needs_env).is_dir()
        # Check the executable from inside the same Linux image used for the app.
        # Host-side existence checks incorrectly accept Windows .venv folders.
        probe = self._execute(
            "env_probe",
            ["python", "-c",
             "import os,sys; p='.venv/bin/python'; sys.exit(0 if os.path.isfile(p) and os.access(p, os.X_OK) else 1)"],
            30,
        )
        return probe.ok

    def setup(self) -> CommandResult | None:
        if not self.stack.setup or self.env_ready():
            return None
        # Do not remove an existing environment when Docker itself is unavailable.
        daemon = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if daemon.returncode != 0:
            return CommandResult("setup", daemon.returncode, daemon.stdout,
                                 (daemon.stderr or "Docker daemon is unavailable.").strip())
        return super().setup()

    def _base_args(self, name: str, network: bool, extra_env: dict[str, str] | None = None, network_name: str | None = None) -> list[str]:
        args = ["docker", "run", "--name", name, "-v", f"{self.root}:/workspace", "-w", "/workspace",
                "--memory", DOCKER_MEMORY, "--cpus", DOCKER_CPUS, "--pids-limit", "512",
                "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONUTF8=1"]
        if hasattr(os, "getuid"):   # keep files in the project folder owned by the current user on Linux/macOS
            args += ["--user", f"{os.getuid()}:{os.getgid()}"]
        if network_name:
            args += ["--network", network_name]
        elif not network:
            args += ["--network", "none"]
        else:
            args += self._cache_args()   # only containers that already have the network (installs)
        for key, value in (extra_env or {}).items():
            args += ["-e", f"{key}={value}"]
        return args

    @staticmethod
    def _cache_args() -> list[str]:
        """Share one package cache between install containers (HOME is /tmp, so pip's own cache dies with each one).

        It is mounted only into containers that have the network, never into the ones that run the
        AI-written tests or the app, so that code cannot tamper with cached packages.
        """
        try:
            (CACHE_DIR / "pip").mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / "npm").mkdir(parents=True, exist_ok=True)
        except OSError:
            return []   # no cache is better than no install
        return ["-v", f"{CACHE_DIR}:/cache", "-e", "PIP_CACHE_DIR=/cache/pip", "-e", "npm_config_cache=/cache/npm"]

    def docker_args(self, name: str, command: list[str], *, network: bool, detach: bool = False,
                    port: int | None = None, env: dict[str, str] | None = None,
                    network_name: str | None = None) -> list[str]:
        extra = {**self.stack.check_env, **(env or {}), **({"PORT": str(port), "HOST": "0.0.0.0"} if port else {})}
        args = self._base_args(name, network, extra, network_name)
        args.insert(2, "-d" if detach else "--rm")
        if port:
            args += ["-p", f"127.0.0.1:{port}:{port}"]
        return args + [self.stack.image] + command

    def _execute(self, name: str, command: list[str], timeout: int, env: dict[str, str] | None = None) -> CommandResult:
        container = f"devagent-{self.root.name}-{uuid.uuid4().hex[:8]}"
        # Installing needs the network. Everything else runs offline, which also enforces
        # the rule that tests must not need the network.
        args = self.docker_args(container, command, network=name in ("install", "setup", "create_venv"), env=env)
        try:
            result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            return CommandResult(name, result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired as exc:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)   # the CLI exiting does not stop it
            return CommandResult(name, -1, _text(exc.stdout), f"{_text(exc.stderr)}\nTimed out after {timeout}s")
        except FileNotFoundError:
            return CommandResult(name, -1, "", "Docker is not installed or not on PATH. Start Docker Desktop, or set RUNNER_MODE=local.")

    def start_app(self, port: int, log_path: Path | None = None, env: dict[str, str] | None = None) -> AppHandle:
        container = f"devagent-app-{self.root.name}-{uuid.uuid4().hex[:8]}"
        runtime_env = {**self.stack.check_env, **(env or {})}
        database_name = network_name = None

        provision_service = self.stack.database_service
        if provision_service in ("postgres", "mysql") and (env or {}).get("QA_RUN") and runtime_env.get("DATABASE_URL", "").startswith("sqlite") and not (env or {}).get("USE_RUNTIME_DATABASE"):
            # The generated unit-test suite uses a fresh SQLite database; the HTTP QA preview
            # still uses the disposable PostgreSQL service configured below when requested.
            provision_service = None

        if provision_service in ("mongo", "postgres", "mysql"):
            # One private network per preview. The database is not published to the host.
            # Preview data persists in a named volume; QA runs use disposable containers.
            network_name = f"devagent-net-{self.root.name}-{uuid.uuid4().hex[:6]}"
            database_name = f"devagent-{provision_service}-{self.root.name}-{uuid.uuid4().hex[:6]}"
            volume_name = f"devagent-{provision_service}-data-{self.root.name}"
            created = subprocess.run(["docker", "network", "create", "--internal", network_name], capture_output=True, text=True)
            if created.returncode != 0:
                raise RuntimeError(f"Could not create the isolated application network: {(created.stderr or created.stdout).strip()}")
            db_args = ["docker", "run", "-d", "--name", database_name, "--network", network_name,
                       "--network-alias", provision_service, "--memory", DOCKER_MEMORY, "--cpus", DOCKER_CPUS,
                       "--pids-limit", "256"]
            if not (env or {}).get("QA_RUN"):
                db_args += ["-v", f"{volume_name}:{'/data/db' if provision_service == 'mongo' else ('/var/lib/postgresql/data' if provision_service == 'postgres' else '/var/lib/mysql')}"]
            if provision_service == "mongo":
                db_args += ["--health-cmd", "mongosh --quiet --eval 'db.adminCommand({ping:1}).ok'",
                            "--health-interval", "3s", "--health-timeout", "3s", "--health-retries", "20", "mongo:7"]
                runtime_env["MONGO_URI"] = "mongodb://mongo:27017/project_database"
            elif provision_service == "postgres":
                from app.projects import get_or_create_database_password
                database_password = get_or_create_database_password(self.root.name, "postgres")
                db_args += ["-e", "POSTGRES_USER=postgres", "-e", f"POSTGRES_PASSWORD={database_password}",
                            "-e", "POSTGRES_DB=app", "--health-cmd", "pg_isready -U postgres -d app",
                            "--health-interval", "3s", "--health-timeout", "3s", "--health-retries", "20",
                            "postgres:16-alpine"]
                if not (env or {}).get("QA_RUN") or (env or {}).get("USE_RUNTIME_DATABASE"):
                    runtime_env["DATABASE_URL"] = f"postgresql+psycopg://postgres:{database_password}@postgres:5432/app"
                runtime_env.pop("USE_RUNTIME_DATABASE", None)
            else:
                from app.projects import get_or_create_database_password
                database_password = get_or_create_database_password(self.root.name, "mysql")
                db_args += ["-e", "MYSQL_ROOT_PASSWORD=" + database_password, "-e", "MYSQL_DATABASE=app",
                            "--health-cmd", 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD"',
                            "--health-interval", "5s", "--health-timeout", "5s", "--health-retries", "30",
                            "--health-start-period", "20s", "mysql:8"]
                if not (env or {}).get("QA_RUN") or (env or {}).get("USE_RUNTIME_DATABASE"):
                    runtime_env["DATABASE_URL"] = f"mysql+pymysql://root:{database_password}@mysql:3306/app"
                runtime_env.pop("USE_RUNTIME_DATABASE", None)
            db = subprocess.run(db_args, capture_output=True, text=True)
            if db.returncode != 0:
                subprocess.run(["docker", "network", "rm", network_name], capture_output=True)
                raise RuntimeError(f"Could not start {provision_service}: {(db.stderr or db.stdout).strip()}")
            ready = False
            for _ in range(40):
                probe = subprocess.run(["docker", "inspect", "-f", "{{.State.Health.Status}}", database_name],
                                       capture_output=True, text=True)
                if probe.stdout.strip() == "healthy":
                    ready = True
                    break
                if probe.stdout.strip() == "unhealthy":
                    break
                time.sleep(1)
            if not ready:
                logs = subprocess.run(["docker", "logs", "--tail", "80", database_name], capture_output=True, text=True)
                subprocess.run(["docker", "rm", "-f", database_name], capture_output=True)
                subprocess.run(["docker", "network", "rm", network_name], capture_output=True)
                raise RuntimeError(f"{provision_service} did not become healthy: {(logs.stdout + logs.stderr)[-2000:]}")

        args = self.docker_args(container, self._fill(self.stack.start, port), network=False,
                                detach=True, port=port, env=runtime_env, network_name=network_name)
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            subprocess.run(["docker", "rm", "-f", database_name], capture_output=True) if database_name else None
            subprocess.run(["docker", "network", "rm", network_name], capture_output=True) if network_name else None
            raise RuntimeError(f"Could not start the container: {(result.stderr or result.stdout).strip()}")
        return DockerAppHandle(container, database_name, network_name)


def make_runner(root: Path, stack=None) -> BaseRunner:
    return DockerRunner(root, stack) if RUNNER_MODE == "docker" else LocalRunner(root, stack)
