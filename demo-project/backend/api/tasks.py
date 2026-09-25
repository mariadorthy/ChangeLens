from backend.services.task_service import get_tasks

def list_tasks() -> list[dict]:
    """API-facing task endpoint placeholder."""
    return get_tasks()
