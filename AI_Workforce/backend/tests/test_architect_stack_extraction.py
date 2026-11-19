from app.agents.architect_context import preferred_stack_for


def test_explicit_srs_technology_choices_are_preserved():
    stack, explicit = preferred_stack_for({
        "constraints": [{"description": "Frontend must use React.js; backend must use Node.js and Express.js; database MongoDB."}]
    })
    assert stack["frontend"] == "React.js"
    assert stack["backend"] == "Express.js"
    assert stack["database"] == "MongoDB"
    assert explicit == {
        "frontend": "React.js",
        "backend": "Express.js",
        "database": "MongoDB",
    }


def test_unspecified_stack_is_marked_assumed_not_binding():
    stack, explicit = preferred_stack_for({"functional_requirements": [{"title": "Create note"}]})
    assert "ASSUMED" in stack["backend"]
    assert "ASSUMED" in stack["database"]
    assert explicit == {}
