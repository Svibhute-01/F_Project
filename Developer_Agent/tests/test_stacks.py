import pytest

from app.schemas.developer import FileChange
from app.stacks import STACKS, detect_stack, infer_stack_from_files, stack_from_architecture
from app.tools.workspace import Workspace


@pytest.mark.parametrize("technologies, expected", [
    ("FastAPI, PostgreSQL, React", "python-fastapi-postgres"),
    ("FastAPI, MySQL", "python-fastapi-mysql"),
    ("Flask, SQLAlchemy", "python-fastapi"),
    ("Express, MongoDB", "node-express"),
    ("React, Node.js", "node-express"),
    ("React, Node.js, Express, MongoDB", "node-react-mongo"),
    ("HTML, CSS", "static-html"),
    ("Flask, Node", "python-fastapi"),   # Python wins when both are named
    ("", "python-fastapi"),
    ("Cobol", "python-fastapi"),
])
def test_stack_detection(technologies, expected):
    assert detect_stack(technologies) == expected


@pytest.mark.parametrize("files, expected", [
    (["package.json", "app.js"], "node-express"),
    (["requirements.txt", "app/main.py"], "python-fastapi"),
    (["index.html", "style.css"], "static-html"),
    ([], None),
])
def test_stack_is_inferred_from_existing_files(files, expected):
    assert infer_stack_from_files(files) == expected


def static_workspace(files: dict[str, str]):
    import uuid
    ws = Workspace("s_" + uuid.uuid4().hex[:8])
    ws.apply_changes([FileChange(path=p, action="create", content=c, explanation="t") for p, c in files.items()])
    return ws


def test_static_site_needs_an_index():
    errors = STACKS["static-html"].structure(static_workspace({"about.html": "<p>x</p>"}))
    assert errors == ["index.html is missing from the project root."]


def test_static_site_links_must_exist():
    page = '<link href="css/style.css" rel="stylesheet"><script src="js/app.js"></script><a href="https://x.dev">x</a><a href="#top">t</a>'
    errors = STACKS["static-html"].structure(static_workspace({"index.html": page, "css/style.css": "a{}"}))
    assert errors == ["index.html links to 'js/app.js', which does not exist in the project."]


def test_static_site_with_all_files_passes_and_handles_nested_pages():
    ws = static_workspace({
        "index.html": '<script src="/js/app.js"></script><a href="docs/page.html">d</a>',
        "docs/page.html": '<link href="../css/s.css" rel="stylesheet">',
        "js/app.js": "1", "css/s.css": "a{}",
    })
    assert STACKS["static-html"].structure(ws) == []


def test_only_python_is_syntax_checked_in_process():
    assert STACKS["python-fastapi"].syntax and not STACKS["node-express"].syntax
    bad = FileChange(path="a.py", action="create", content="def x(:\n", explanation="t")
    assert STACKS["python-fastapi"].syntax([bad])


def test_probe_rules_differ_per_stack():
    assert STACKS["python-fastapi"].probe_ok(404)      # an API may have no page at "/"
    assert not STACKS["python-fastapi"].probe_ok(500)
    assert STACKS["static-html"].probe_ok(200) and not STACKS["static-html"].probe_ok(404)


def test_react_express_mongo_architecture_is_supported_by_its_runtime_profile():
    from app.stacks import check_contract
    stack = STACKS["node-react-mongo"]
    result = check_contract(stack, [
        {"role": "frontend", "technology": "React.js with Vite"},
        {"role": "backend", "technology": "Node.js with Express.js"},
        {"role": "database", "technology": "MongoDB with Mongoose"},
    ])
    assert result["unsupported"] == []
    assert stack.database_service == "mongo"
    assert "build" in stack.commands and "test" in stack.commands


def test_architect_stack_is_authoritative_for_react_express_mongodb():
    architecture = [
        {"role": "frontend", "technology": "React.js", "component": "Frontend Application"},
        {"role": "backend", "technology": "Express.js", "component": "Backend API Service"},
        {"role": "database", "technology": "MongoDB", "component": "Database"},
    ]
    assert stack_from_architecture(architecture) == "node-react-mongo"


def test_architect_stack_does_not_fall_back_to_python_for_unknown_architecture():
    architecture = [
        {"role": "frontend", "technology": "Vue.js"},
        {"role": "backend", "technology": "Spring Boot"},
        {"role": "database", "technology": "MongoDB"},
    ]
    assert stack_from_architecture(architecture) is None


def test_architect_stack_selects_fastapi_postgres_from_component_decisions():
    architecture = [
        {"role": "frontend", "technology": "HTML, CSS, JavaScript"},
        {"role": "backend", "technology": "Python with FastAPI"},
        {"role": "database", "technology": "PostgreSQL"},
    ]
    assert stack_from_architecture(architecture) == "python-fastapi-postgres"


def test_architecture_prompt_requires_removing_obsolete_stack_files():
    from app.stacks import contract_text
    prompt = contract_text([
        {"role": "frontend", "technology": "React.js"},
        {"role": "backend", "technology": "Express.js"},
        {"role": "database", "technology": "MongoDB"},
    ], [])
    assert "existing files belong to a different stack" in prompt
    assert "delete changes for obsolete incompatible files" in prompt
