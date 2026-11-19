"""Builds the System Architect's input from the saved Requirements Analyst and Project Manager output.

The Architect never reads the SRS. Its inputs are the validated outputs of the two earlier
agents *for this project*: the requirements (re-used from ``pm_context`` so the ids are
exactly the ones the Project Manager saw) and the project plan. Every query is filtered by
``project_id``, and the id sets built here are what the design is later validated against.
"""

from dataclasses import dataclass, field
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PMEpic, PMPlan, PMSprint, PMTask, PMTaskDependency, Project
from .architect_validation import ReferenceIds
from .pm_context import MissingRequirementsError, RequirementsContext, build_requirements_context

__all__ = ["ArchitectContext", "MissingPlanError", "MissingRequirementsError", "build_architect_context"]

# Used only when the SRS does not specify a technology. Explicit SRS choices take priority.
DEFAULT_ASSUMED_STACK = {
    "backend": "Python with FastAPI and SQLAlchemy (ASSUMED; SRS does not specify)",
    "database": "PostgreSQL (ASSUMED; SRS does not specify)",
    "frontend": "Server-rendered HTML with Jinja2, CSS and JavaScript (ASSUMED; SRS does not specify)",
    "ai": "No AI service unless required (ASSUMED)",
}
# Backward-compatible name for older tests/integrations; new runs use preferred_stack_for().
PREFERRED_STACK = DEFAULT_ASSUMED_STACK

_TECH_PATTERNS = {
    "frontend": [(r"\breact(?:\.js)?\b", "React.js"), (r"\bvue(?:\.js)?\b", "Vue.js"),
                  (r"\bangular\b", "Angular"), (r"\bsvelte\b", "Svelte"),
                  (r"\bhtml\b", "HTML/CSS/JavaScript")],
    "backend": [(r"\bexpress(?:\.js)?\b", "Express.js"), (r"\bfastapi\b", "FastAPI"),
                 (r"\bdjango\b", "Django"), (r"\bflask\b", "Flask"),
                 (r"\bspring(?: boot)?\b", "Spring Boot"),
                 (r"\bnode(?:\.js)?\b", "Node.js"), (r"\bpython\b", "Python")],
    "database": [(r"\bmongodb\b|\bmongo\b", "MongoDB"), (r"\bpostgres(?:ql)?\b", "PostgreSQL"),
                  (r"\bmysql\b", "MySQL"), (r"\bsqlite\b", "SQLite"),
                  (r"\bredis\b", "Redis")],
}


def preferred_stack_for(requirements_payload: dict) -> tuple[dict, dict[str, str]]:
    """Extract explicit technologies from Requirements Analyst output; mark defaults as assumed.

    Returns (stack_for_architect_prompt, explicit_role_choices). The second value is used by
    deterministic validation, so inferred defaults are never mistaken for SRS requirements.
    """
    text = json.dumps(requirements_payload, ensure_ascii=False).lower()
    selected: dict[str, str] = {}
    explicit: dict[str, str] = {}
    for role, patterns in _TECH_PATTERNS.items():
        match = next((label for pattern, label in patterns if re.search(pattern, text)), None)
        if match:
            # Keep the most specific matching framework/runtime for each layer.
            selected[role] = match
            explicit[role] = match
        else:
            selected[role] = DEFAULT_ASSUMED_STACK[role]
    selected["ai"] = "Use only if required by the SRS; otherwise none"
    return selected, explicit

_DESCRIPTION_LIMIT = 400


class MissingPlanError(RuntimeError):
    """The project has no usable Project Manager plan."""


@dataclass
class ArchitectContext:
    requirements: RequirementsContext
    plan_run_id: int | None
    plan_payload: dict
    references: ReferenceIds
    warnings: list[str] = field(default_factory=list)
    preferred_stack: dict = field(default_factory=dict)
    explicit_stack: dict = field(default_factory=dict)

    @property
    def requirements_run_id(self) -> int:
        return self.requirements.requirements_run_id


def _clip(text: str | None) -> str:
    text = (text or "").strip()
    return text if len(text) <= _DESCRIPTION_LIMIT else text[: _DESCRIPTION_LIMIT - 3] + "..."


def build_architect_context(db: Session, project: Project) -> ArchitectContext:
    """Load and validate the Requirements Analyst and Project Manager output for one project."""
    requirements = build_requirements_context(db, project)  # raises MissingRequirementsError

    plan = db.scalar(select(PMPlan).where(PMPlan.project_id == project.id))
    if plan is None:
        raise MissingPlanError("No Project Manager plan exists for this project. Run the Project Manager first.")

    def rows(model, *order):
        return db.scalars(
            select(model).where(model.project_id == project.id, model.plan_id == plan.id).order_by(*order)
        ).all()

    tasks = rows(PMTask, PMTask.execution_index, PMTask.id)
    if not tasks:
        raise MissingPlanError("The Project Manager plan contains no tasks, so there is nothing to design against.")
    epics = rows(PMEpic, PMEpic.id)
    sprints = rows(PMSprint, PMSprint.sequence)
    dependencies = rows(PMTaskDependency, PMTaskDependency.id)

    warnings: list[str] = []
    if plan.requirements_run_id != requirements.requirements_run_id:
        warnings.append(
            "The requirements were re-analyzed after the project plan was generated; "
            "the design uses the newest requirements and the existing plan."
        )

    payload = {
        "execution_summary": plan.execution_summary,
        "epics": [
            {"id": e.epic_id, "title": e.title, "description": _clip(e.description), "requirement_ids": e.related_requirement_ids}
            for e in epics
        ],
        "tasks": [
            {
                "id": t.task_id,
                "epic": t.epic_id,
                "title": t.title,
                "description": _clip(t.description),
                "requirement_id": t.related_requirement_id,
                "story_id": t.related_story_id,
                "role": t.suggested_role,
                "sprint": t.sprint_id,
            }
            for t in tasks
        ],
        "task_dependencies": [
            {"task": d.task_id, "depends_on": d.depends_on_task_id, "type": d.dependency_type} for d in dependencies
        ],
        "sprints": [{"id": s.sprint_id, "name": s.name, "goal": _clip(s.goal)} for s in sprints],
        "assumptions": plan.assumptions or [],
    }
    references = ReferenceIds.build(
        requirement_ids=requirements.artifact_ids,
        task_ids=[t.task_id for t in tasks],
        titles=requirements.titles,
    )
    preferred_stack, explicit_stack = preferred_stack_for(requirements.payload)
    return ArchitectContext(
        requirements=requirements,
        plan_run_id=plan.agent_run_id,
        plan_payload=payload,
        references=references,
        warnings=warnings,
        preferred_stack=preferred_stack,
        explicit_stack=explicit_stack,
    )
