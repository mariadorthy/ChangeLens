from pathlib import Path
import sys


DEMO_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(DEMO_PROJECT_ROOT) in sys.path:
    sys.path.remove(str(DEMO_PROJECT_ROOT))

sys.path.insert(0, str(DEMO_PROJECT_ROOT))

for module_name in list(sys.modules):
    if module_name == "backend" or module_name.startswith("backend."):
        del sys.modules[module_name]

from backend.services.task_service import get_tasks


def test_get_tasks_returns_task_shape() -> None:
    """Verify the task service still returns the expected task shape."""
    tasks = get_tasks()
    assert tasks
    assert set(tasks[0]) == {"id", "title", "completed"}