import subprocess
import sys

import pytest

from app.stacks import STACKS, get_stack, rules_for
from app.tools import runner as runner_module
from app.tools.runner import TIMEOUTS, DockerRunner, LocalRunner, safe_env


def test_timeout_keeps_the_partial_output(tmp_path, monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output=b"Collecting fastapi\n", stderr=b"building wheel")

    monkeypatch.setattr(runner_module.subprocess, "run", slow)
    result = LocalRunner(tmp_path).run("install")
    assert not result.ok
    summary = result.summary()
    assert "Collecting fastapi" in summary and "building wheel" in summary
    assert f"Timed out after {TIMEOUTS['install']}s" in summary


def test_install_prefers_wheels_and_has_the_longest_limit(tmp_path):
    command = LocalRunner(tmp_path)._commands()["install"]
    assert "--prefer-binary" in command
    assert TIMEOUTS["install"] > TIMEOUTS["test"] > TIMEOUTS["check_imports"]


def test_unknown_commands_are_still_refused(tmp_path):
    with pytest.raises(ValueError):
        LocalRunner(tmp_path).run("rm -rf /")


def test_child_processes_never_see_secrets(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "gemini-secret")
    monkeypatch.setenv("DEVELOPER_SERVICE_KEY", "service-secret")
    monkeypatch.setenv("SOME_OTHER_TOKEN", "x")
    env = safe_env({"PORT": "9100"})
    assert "GOOGLE_API_KEY" not in env and "DEVELOPER_SERVICE_KEY" not in env and "SOME_OTHER_TOKEN" not in env
    assert env["PORT"] == "9100" and "PATH" in env


def test_a_real_child_process_cannot_read_the_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "gemini-secret")
    result = LocalRunner(tmp_path)._execute(
        "probe", [sys.executable, "-c", "import os; print(os.environ.get('GOOGLE_API_KEY', 'absent'))"], 30)
    assert result.stdout.strip() == "absent"


@pytest.mark.parametrize("stack_id", list(STACKS))
def test_every_stack_rules_template_renders(stack_id):
    rules = rules_for(get_stack(stack_id))
    assert "ENVIRONMENT RULES" in rules and "{python_version}" not in rules


def test_python_rules_mention_what_the_checks_need():
    rules = rules_for(get_stack("python-fastapi"))
    for needle in ("requirements.txt", "psycopg2", "bcrypt", "SQLite", "tests/", "uvicorn app.main:app"):
        assert needle in rules


def test_node_commands_use_the_node_tools(tmp_path):
    commands = LocalRunner(tmp_path, get_stack("node-express"))._commands()
    assert set(commands) == {"install", "check_imports", "test"}
    assert commands["check_imports"][1:] == ["-e", "require('./app')"]


# --- Docker: the exact commands (no Docker daemon is needed to check these) ---------------------

def docker(tmp_path, stack_id="python-fastapi"):
    return DockerRunner(tmp_path, get_stack(stack_id))


def test_docker_mounts_only_the_project_and_limits_resources(tmp_path):
    runner = docker(tmp_path)
    args = runner.docker_args("c1", ["echo", "hi"], network=False)
    assert args[:3] == ["docker", "run", "--rm"]
    assert f"{tmp_path}:/workspace" in args and "--memory" in args and "--cpus" in args and "--pids-limit" in args
    assert args[args.index("--network") + 1] == "none"
    assert args[-3:] == [get_stack("python-fastapi").image, "echo", "hi"]
    assert not any("GOOGLE_API_KEY" in part or "SERVICE_KEY" in part for part in args)


def test_docker_only_gives_the_network_to_installs(tmp_path, monkeypatch):
    seen = []

    def fake_run(args, **kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    runner = docker(tmp_path)
    runner.run("install")
    runner.run("test")
    install = next(args for args in seen if "pip" in args)
    test = next(args for args in seen if "pytest" in args)
    assert "--network" not in install
    assert test[test.index("--network") + 1] == "none"


def test_docker_app_publishes_the_port_on_localhost_only(tmp_path):
    args = docker(tmp_path).docker_args("c2", ["x"], network=False, detach=True, port=9101)
    assert args[2] == "-d"
    assert "127.0.0.1:9101:9101" in args
    assert "PORT=9101" in args and "HOST=0.0.0.0" in args


def test_docker_uses_the_linux_paths_inside_the_container(tmp_path):
    commands = docker(tmp_path)._commands()
    assert commands["test"][0] == ".venv/bin/python"
    assert docker(tmp_path, "node-express")._commands()["install"][0] == "npm"


def test_a_timed_out_docker_command_removes_its_container(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[1] == "run":
            raise subprocess.TimeoutExpired(args, 1, output=b"", stderr=b"")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    result = docker(tmp_path).run("test", timeout=1)
    assert not result.ok and "Timed out" in result.summary()
    assert any(args[:3] == ["docker", "rm", "-f"] for args in calls)


def test_missing_docker_gives_a_helpful_message(tmp_path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    assert "RUNNER_MODE=local" in docker(tmp_path).run("test").summary()


def test_react_mongo_preview_provisions_private_database_and_keeps_volume(tmp_path, monkeypatch):
    from app.stacks import get_stack
    from app.tools.runner import DockerRunner

    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["docker", "inspect", "-f"]:
            return subprocess.CompletedProcess(args, 0, "healthy", "")
        return subprocess.CompletedProcess(args, 0, "container-id", "")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    runner = DockerRunner(tmp_path, get_stack("node-react-mongo"))
    handle = runner.start_app(9123, env={})
    db_run = next(args for args in calls if args[:3] == ["docker", "run", "-d"] and "mongo:7" in args)
    app_run = next(args for args in calls if args[:3] == ["docker", "run", "-d"] and get_stack("node-react-mongo").image in args)
    assert "--network-alias" in db_run and "mongo" in db_run
    assert any(part.endswith(":/data/db") for part in db_run)
    assert app_run[app_run.index("--network") + 1] in db_run[db_run.index("--network") + 1:db_run.index("--network") + 2]
    assert "MONGO_URI=mongodb://mongo:27017/project_database" in app_run
    handle.stop()
    stop_calls = calls[len(calls)-3:]
    assert any(args[:3] == ["docker", "rm", "-f"] for args in stop_calls)
    assert not any(args[:3] == ["docker", "volume", "rm"] for args in calls)


def test_react_mongo_qa_database_is_disposable(tmp_path, monkeypatch):
    from app.stacks import get_stack
    from app.tools.runner import DockerRunner
    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["docker", "inspect", "-f"]:
            return subprocess.CompletedProcess(args, 0, "healthy", "")
        return subprocess.CompletedProcess(args, 0, "container-id", "")
    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    runner = DockerRunner(tmp_path, get_stack("node-react-mongo"))
    runner.start_app(9124, env={"QA_RUN": "true"})
    db_run = next(args for args in calls if args[:3] == ["docker", "run", "-d"] and "mongo:7" in args)
    assert "-v" not in db_run


@pytest.mark.parametrize("stack_id, image, url_prefix", [
    ("python-fastapi-postgres", "postgres:16-alpine", "postgresql+psycopg://postgres:"),
    ("python-fastapi-mysql", "mysql:8", "mysql+pymysql://root:"),
])
def test_sql_database_services_are_created_with_generated_passwords(tmp_path, monkeypatch, stack_id, image, url_prefix):
    from app.stacks import get_stack
    from app.tools.runner import DockerRunner
    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["docker", "inspect", "-f"]:
            return subprocess.CompletedProcess(args, 0, "healthy", "")
        return subprocess.CompletedProcess(args, 0, "container-id", "")
    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    runner = DockerRunner(tmp_path, get_stack(stack_id))
    runner.start_app(9125, env={"QA_RUN": "true", "USE_RUNTIME_DATABASE": "true"})
    db_run = next(args for args in calls if args[:3] == ["docker", "run", "-d"] and image in args)
    app_run = next(args for args in calls if args[:3] == ["docker", "run", "-d"] and get_stack(stack_id).image in args)
    assert any(arg.startswith("POSTGRES_PASSWORD=") or arg.startswith("MYSQL_ROOT_PASSWORD=") for arg in db_run)
    url = next(arg for arg in app_run if arg.startswith("DATABASE_URL="))
    assert url.startswith("DATABASE_URL=" + url_prefix)
    assert "-v" not in db_run  # QA database is disposable


def test_local_python_environment_requires_the_platform_executable(tmp_path):
    runner = LocalRunner(tmp_path, get_stack("python-fastapi"))
    (tmp_path / ".venv").mkdir()
    # A directory left by a different OS is not a ready environment.
    assert not runner.env_ready()


def test_docker_python_environment_is_probed_inside_linux_image(tmp_path, monkeypatch):
    runner = docker(tmp_path)
    calls = []

    def fake_execute(name, command, timeout, env=None):
        calls.append((name, command, timeout))
        return runner_module.CommandResult(name, 0, "", "")

    monkeypatch.setattr(runner, "_execute", fake_execute)
    assert runner.env_ready()
    assert calls[0][0] == "env_probe"
    assert ".venv/bin/python" in calls[0][1][-1]


def test_docker_python_environment_not_ready_when_linux_executable_missing(tmp_path, monkeypatch):
    runner = docker(tmp_path)
    monkeypatch.setattr(
        runner, "_execute",
        lambda name, command, timeout, env=None: runner_module.CommandResult(name, 1, "", "missing"),
    )
    assert not runner.env_ready()
