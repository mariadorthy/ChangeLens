from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from analyzer.git_diff.service import (
    ChangeDetectionError,
    ChangeSet,
    ChangedFile,
    extract_changed_files,
)
from analyzer.impact_analyzer import (
    ImpactReport,
    ImpactResult,
    Relationship,
    discover_relationships,
)
from analyzer.completeness_analyzer import analyze_completeness

def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "ChangeLens Tests")
    return repo, ""


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def test_modified_file_reports_status_counts_hunks_and_lines(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "tasks.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "tasks.py").write_text("one\ntwo changed\nthree\nfour\n", encoding="utf-8")
    target = _commit(repo, "modify")

    result = extract_changed_files(str(repo), base, target)

    changed = result.files[0]
    assert changed.path == "tasks.py"
    assert changed.status == "modified"
    assert changed.additions == 2
    assert changed.deletions == 1
    assert changed.hunks
    assert changed.hunks[0].old_start == 2
    assert changed.hunks[0].new_start == 2
    assert "two changed" in changed.added_lines
    assert "two" in changed.removed_lines


def test_added_file(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "new.py").write_text("print('new')\n", encoding="utf-8")
    target = _commit(repo, "add")

    result = extract_changed_files(str(repo), base, target)

    assert [(f.path, f.status) for f in result.files] == [("new.py", "added")]
    assert result.files[0].additions == 1
    assert result.files[0].deletions == 0


def test_deleted_file(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "remove.py").write_text("print('remove')\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "remove.py").unlink()
    target = _commit(repo, "delete")

    result = extract_changed_files(str(repo), base, target)

    assert [(f.path, f.status) for f in result.files] == [("remove.py", "deleted")]
    assert result.files[0].additions == 0
    assert result.files[0].deletions == 1


def test_multiple_changed_files(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "one.txt").write_text("one\n", encoding="utf-8")
    (repo / "two.txt").write_text("two\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "one.txt").write_text("one changed\n", encoding="utf-8")
    (repo / "three.txt").write_text("three\n", encoding="utf-8")
    (repo / "two.txt").unlink()
    target = _commit(repo, "multiple")

    result = extract_changed_files(str(repo), base, target)

    assert {(f.path, f.status) for f in result.files} == {
        ("one.txt", "modified"),
        ("three.txt", "added"),
        ("two.txt", "deleted"),
    }


def test_rename_is_detected_when_git_reports_it(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "old.txt").write_text("same content\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "old.txt").rename(repo / "new.txt")
    target = _commit(repo, "rename")

    result = extract_changed_files(str(repo), base, target)

    assert len(result.files) == 1
    assert result.files[0].status == "renamed"
    assert result.files[0].old_path == "old.txt"
    assert result.files[0].path == "new.txt"

def test_invalid_revision_raises_clear_error(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    commit = _commit(repo, "base")

    with pytest.raises(ChangeDetectionError, match="Invalid base revision"):
        extract_changed_files(str(repo), "does-not-exist", commit)

def _write(repo: Path, relative_path: str, content: str) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_python_import_relationship_is_high_confidence(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "module_a.py",
        "def get_value():\n    return 1\n",
    )
    _write(
        repo,
        "module_b.py",
        "from module_a import get_value\n\n"
        "def use_value():\n"
        "    return get_value()\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "module_a.py",
        "def get_value():\n    return 2\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "module_b.py"
        and relationship.type == "import"
        and relationship.confidence == "high"
        for relationship in relationships
    )


def test_frontend_import_relationship_is_detected(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "frontend/services/tasks.js",
        "export function getTasks() {\n"
        "  return fetch('/api/tasks')\n"
        "}\n",
    )
    _write(
        repo,
        "frontend/components/TaskList.jsx",
        "import { getTasks } from '../services/tasks.js'\n\n"
        "export function TaskList() {\n"
        "  return null\n"
        "}\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "frontend/services/tasks.js",
        "export function getTasks() {\n"
        "  return fetch('/api/tasks?limit=20')\n"
        "}\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "frontend/components/TaskList.jsx"
        and relationship.type == "import"
        and relationship.confidence == "high"
        for relationship in relationships
    )


def test_api_consumer_relationship_is_detected(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "backend/api/tasks.py",
        "from backend.services.task_service import get_tasks\n\n"
        "@router.get('/api/tasks')\n"
        "def list_tasks():\n"
        "    return get_tasks()\n",
    )
    _write(
        repo,
        "frontend/services/api.js",
        "export async function fetchTasks() {\n"
        "  return fetch('/api/tasks')\n"
        "}\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "backend/api/tasks.py",
        "from backend.services.task_service import get_tasks\n\n"
        "@router.get('/api/tasks')\n"
        "def list_tasks():\n"
        "    return get_tasks()\n"
        "\n"
        "# changed implementation\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "frontend/services/api.js"
        and relationship.type == "api_consumer"
        and relationship.confidence == "high"
        for relationship in relationships
    )


def test_test_relationship_is_detected(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "task_service.py",
        "def get_tasks():\n"
        "    return []\n",
    )
    _write(
        repo,
        "tests/test_task_service.py",
        "from task_service import get_tasks\n\n"
        "def test_get_tasks():\n"
        "    assert get_tasks() == []\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "task_service.py",
        "def get_tasks():\n"
        "    return [{'id': 1}]\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "tests/test_task_service.py"
        and relationship.type == "test"
        and relationship.confidence == "high"
        for relationship in relationships
    )


def test_documentation_relationship_is_detected(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "backend/api/tasks.py",
        "@router.get('/api/tasks')\n"
        "def list_tasks():\n"
        "    return []\n",
    )
    _write(
        repo,
        "docs/tasks.md",
        "# Tasks\n\n"
        "The API exposes `GET /api/tasks`.\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "backend/api/tasks.py",
        "@router.get('/api/tasks')\n"
        "def list_tasks():\n"
        "    return [{'id': 1}]\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "docs/tasks.md"
        and relationship.type == "documentation"
        for relationship in relationships
    )


def test_configuration_relationship_is_detected(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "config/settings.json",
        '{"default_page_size": 20}\n',
    )
    _write(
        repo,
        "backend/services/task_service.py",
        "CONFIG_PATH = 'config/settings.json'\n\n"
        "def get_tasks():\n"
        "    return []\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "config/settings.json",
        '{"default_page_size": 50}\n',
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert any(
        relationship.path == "backend/services/task_service.py"
        and relationship.type == "configuration"
        and relationship.confidence == "high"
        for relationship in relationships
    )


def test_unrelated_file_is_not_reported(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)

    _write(
        repo,
        "task_service.py",
        "def get_tasks():\n"
        "    return []\n",
    )
    _write(
        repo,
        "utils/date.py",
        "def today():\n"
        "    return 'today'\n",
    )

    base = _commit(repo, "base")

    _write(
        repo,
        "task_service.py",
        "def get_tasks():\n"
        "    return [{'id': 1}]\n",
    )
    target = _commit(repo, "change")

    change_set = extract_changed_files(str(repo), base, target)
    report = discover_relationships(str(repo), change_set)

    relationships = report.changed_files[0].relationships

    assert all(
        relationship.path != "utils/date.py"
        for relationship in relationships
    )

def _phase4_change_set(
    *files: ChangedFile,
) -> ChangeSet:
    return ChangeSet(
        repository="test-repository",
        base_revision="base",
        target_revision="target",
        files=tuple(files),
    )


def _phase4_changed_file(
    path: str,
    *,
    status: str = "modified",
    old_path: str | None = None,
) -> ChangedFile:
    return ChangedFile(
        path=path,
        status=status,
        old_path=old_path,
        additions=1,
        deletions=0,
        hunks=(),
        added_lines=(),
        removed_lines=(),
    )


def _phase4_impact_report(
    changed_file: str,
    *relationships: Relationship,
) -> ImpactReport:
    return ImpactReport(
        repository="test-repository",
        changed_files=(
            ImpactResult(
                changed_file=changed_file,
                relationships=tuple(relationships),
            ),
        ),
    )


def _phase4_relationship(
    path: str,
    relationship_type: str,
    *,
    reason: str = "Evidence-backed relationship",
    confidence: str = "high",
) -> Relationship:
    return Relationship(
        path=path,
        type=relationship_type,
        reason=reason,
        confidence=confidence,
    )


def test_completeness_complete_change_has_no_missing_work() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
        _phase4_changed_file("tests/test_task_service.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service.py",
        _phase4_relationship(
            "tests/test_task_service.py",
            "test",
            reason="Test imports the changed Python module",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "complete"
    assert report.potentially_missing == ()
    assert len(report.affected_and_changed) == 1
    assert report.affected_and_changed[0].path == "tests/test_task_service.py"


def test_completeness_missing_test_is_potentially_incomplete() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service.py",
        _phase4_relationship(
            "tests/test_task_service.py",
            "test",
            reason="Test imports the changed Python module",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"
    assert len(report.potentially_missing) == 1

    missing = report.potentially_missing[0]

    assert missing.path == "tests/test_task_service.py"
    assert missing.relationship_types == ("test",)
    assert missing.reasons == (
        "Test imports the changed Python module",
    )
    assert missing.confidences == ("high",)


def test_completeness_missing_api_consumer_is_reported() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/api/tasks.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/api/tasks.py",
        _phase4_relationship(
            "frontend/src/api/tasks.js",
            "api_consumer",
            reason="Frontend consumer references the changed API route",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"
    assert len(report.potentially_missing) == 1

    missing = report.potentially_missing[0]

    assert missing.path == "frontend/src/api/tasks.js"
    assert missing.relationship_types == ("api_consumer",)
    assert missing.confidences == ("high",)


def test_completeness_missing_documentation_is_reported() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service.py",
        _phase4_relationship(
            "docs/tasks.md",
            "documentation",
            reason="Documentation references the changed component",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"
    assert len(report.potentially_missing) == 1

    missing = report.potentially_missing[0]

    assert missing.path == "docs/tasks.md"
    assert missing.relationship_types == ("documentation",)
    assert missing.confidences == ("high",)


def test_completeness_multiple_relationships_same_file_are_aggregated() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service.py",
        _phase4_relationship(
            "tests/test_task_service.py",
            "test",
            reason="Test imports the changed Python module",
            confidence="high",
        ),
        _phase4_relationship(
            "tests/test_task_service.py",
            "reference",
            reason="Test references the changed service",
            confidence="medium",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"
    assert len(report.potentially_missing) == 1

    missing = report.potentially_missing[0]

    assert missing.path == "tests/test_task_service.py"
    assert missing.relationship_types == ("reference", "test")
    assert missing.reasons == (
        "Test imports the changed Python module",
        "Test references the changed service",
    )
    assert missing.confidences == ("high", "medium")


def test_completeness_unrelated_file_is_not_missing() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service.py",
        _phase4_relationship(
            "tests/test_task_service.py",
            "test",
            reason="Test imports the changed Python module",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert all(
        artifact.path != "utils/date.py"
        for artifact in report.potentially_missing
    )


def test_completeness_rename_does_not_report_old_path_as_missing() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file(
            "backend/services/task_service_v2.py",
            status="renamed",
            old_path="backend/services/task_service.py",
        ),
    )

    impact_report = _phase4_impact_report(
        "backend/services/task_service_v2.py",
        _phase4_relationship(
            "backend/services/task_service.py",
            "import",
            reason="Existing relationship points to the renamed module",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "complete"
    assert report.potentially_missing == ()


def test_completeness_deleted_artifact_is_not_automatically_missing() -> None:
    change_set = _phase4_change_set(
        _phase4_changed_file(
            "docs/old-tasks.md",
            status="deleted",
        ),
    )

    impact_report = _phase4_impact_report(
        "docs/old-tasks.md",
        _phase4_relationship(
            "docs/old-tasks.md",
            "documentation",
            reason="Deleted documentation referenced the changed component",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "complete"
    assert report.potentially_missing == ()