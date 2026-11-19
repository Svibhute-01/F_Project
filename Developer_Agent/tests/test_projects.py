import json

from app import projects


def test_database_password_is_stable_and_does_not_overwrite_stack(tmp_path, monkeypatch):
    monkeypatch.setattr(projects, "PROJECTS_DIR", tmp_path)
    projects.set_stack_id("project_7", "python-fastapi-postgres")
    first = projects.get_or_create_database_password("project_7", "postgres")
    second = projects.get_or_create_database_password("project_7", "postgres")
    assert first == second and len(first) >= 24
    data = json.loads((tmp_path / "project_7.json").read_text())
    assert data["stack"] == "python-fastapi-postgres"
    assert data["database_passwords"]["postgres"] == first
