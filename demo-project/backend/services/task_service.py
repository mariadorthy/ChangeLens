from backend.models.task import Task


def get_tasks() -> list[dict]:
    """Return the demo task collection."""
    return [Task(id=1, title="Prepare Phase 4 final demo", completed=False).to_dict()]
