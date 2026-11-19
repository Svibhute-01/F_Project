"""Persistent per-project runtime metadata (stack choice and local database secrets)."""
import json
import secrets

from app.config import PROJECTS_DIR


def _path(project_id: str):
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR / f"{project_id}.json"


def _read(project_id: str) -> dict:
    try:
        value = json.loads(_path(project_id).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def get_stack_id(project_id: str) -> str | None:
    return _read(project_id).get("stack")


def set_stack_id(project_id: str, stack_id: str) -> None:
    data = _read(project_id)
    data["stack"] = stack_id
    _path(project_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_or_create_database_password(project_id: str, service: str) -> str:
    """Return a stable random local DB password so persistent volumes remain usable on restart."""
    data = _read(project_id)
    passwords = data.setdefault("database_passwords", {})
    password = passwords.get(service)
    if not password:
        password = secrets.token_urlsafe(24)
        passwords[service] = password
        path = _path(project_id)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return password
