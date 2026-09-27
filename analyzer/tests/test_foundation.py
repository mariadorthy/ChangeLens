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


def test_completeness_co_deleted_related_artifact_is_not_reported_as_missing() -> None:
    """A related artifact that is also deleted in the same change set must not
    appear in potentially_missing.  Previously the existing deleted-file guard
    (lines 181-186 of completeness_analyzer/service.py) was only exercised
    through the self-referential case (deleted file whose relationship points
    back to itself).  This test exercises the cross-file variant: module.py is
    deleted AND tests/test_module.py is also deleted; the impact report names
    tests/test_module.py as a relationship of module.py, so without the guard
    it would be misclassified as potentially_missing."""
    change_set = _phase4_change_set(
        _phase4_changed_file("module.py", status="deleted"),
        _phase4_changed_file("tests/test_module.py", status="deleted"),
    )

    impact_report = _phase4_impact_report(
        "module.py",
        _phase4_relationship(
            "tests/test_module.py",
            "test",
            reason="Imports Python module represented by module.py",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "complete"
    assert report.potentially_missing == ()
    assert report.affected_and_changed == ()


def test_completeness_multiple_changed_files_sharing_one_artifact_changed() -> None:
    """Two changed files each discover the same related artifact via different
    relationship types.  When that artifact is also changed the completeness
    engine must merge both relationships into a single affected_and_changed
    entry and must NOT report it as potentially_missing (Case 3 + Case 5)."""
    change_set = _phase4_change_set(
        _phase4_changed_file("service_a.py"),
        _phase4_changed_file("service_b.py"),
        _phase4_changed_file("tests/test_shared.py"),
    )

    impact_report = ImpactReport(
        repository="test-repository",
        changed_files=(
            ImpactResult(
                changed_file="service_a.py",
                relationships=(
                    _phase4_relationship(
                        "tests/test_shared.py",
                        "test",
                        reason="Imports service_a",
                    ),
                ),
            ),
            ImpactResult(
                changed_file="service_b.py",
                relationships=(
                    _phase4_relationship(
                        "tests/test_shared.py",
                        "reference",
                        reason="References service_b",
                        confidence="medium",
                    ),
                ),
            ),
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "complete"
    assert report.potentially_missing == ()
    assert len(report.affected_and_changed) == 1

    artifact = report.affected_and_changed[0]

    assert artifact.path == "tests/test_shared.py"
    assert artifact.relationship_types == ("reference", "test")
    assert artifact.reasons == ("Imports service_a", "References service_b")
    assert set(artifact.confidences) == {"high", "medium"}


def test_completeness_mixed_some_related_changed_some_missing() -> None:
    """One changed file has two related artifacts: one that was also changed
    (should appear in affected_and_changed) and one that was not (should appear
    in potentially_missing).  Status must be potentially_incomplete and
    recommendations must cover both the affected_and_changed and
    potentially_missing relationship types (Case 6)."""
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
        _phase4_changed_file("tests/test_task_service.py"),
        # docs/tasks.md intentionally NOT changed
    )

    impact_report = ImpactReport(
        repository="test-repository",
        changed_files=(
            ImpactResult(
                changed_file="backend/services/task_service.py",
                relationships=(
                    _phase4_relationship(
                        "tests/test_task_service.py",
                        "test",
                        reason="Imports the changed Python module",
                        confidence="high",
                    ),
                    _phase4_relationship(
                        "docs/tasks.md",
                        "documentation",
                        reason="Documents the changed service",
                        confidence="medium",
                    ),
                ),
            ),
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"

    assert len(report.affected_and_changed) == 1
    assert report.affected_and_changed[0].path == "tests/test_task_service.py"

    assert len(report.potentially_missing) == 1
    missing = report.potentially_missing[0]
    assert missing.path == "docs/tasks.md"
    assert missing.relationship_types == ("documentation",)
    assert missing.confidences == ("medium",)

    # Recommendations now cover all discovered relationships, including those
    # for artifacts that were already changed — both the test (affected_and_changed,
    # type=test) and the docs (potentially_missing, type=documentation).
    assert "Review affected documentation" in report.validation_recommendations
    assert "Run related tests" in report.validation_recommendations



def test_completeness_complete_change_includes_recommendations_for_affected_artifacts() -> None:
    """When all related artifacts were also changed (status == complete),
    validation_recommendations must still include actions derived from those
    affected_and_changed relationship types.

    Previously, recommendations were generated only from potentially_missing
    artifacts, so a fully-complete change always returned an empty
    recommendation list — silently dropping actionable guidance such as
    'Run related tests' even when the developer changed the test file."""
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
    # The test was changed — no missing work — but running it is still required.
    assert "Run related tests" in report.validation_recommendations


def test_completeness_mixed_recommendations_cover_both_affected_and_missing() -> None:
    """When some related artifacts were changed and others were not, the
    validation_recommendations must include guidance derived from both
    affected_and_changed and potentially_missing relationship types.

    In the scenario below: the test file was changed (affected_and_changed,
    type=test) and the docs were NOT changed (potentially_missing,
    type=documentation).  Both 'Run related tests' and
    'Review affected documentation' must appear."""
    change_set = _phase4_change_set(
        _phase4_changed_file("backend/services/task_service.py"),
        _phase4_changed_file("tests/test_task_service.py"),
        # docs/tasks.md intentionally NOT changed
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
            "docs/tasks.md",
            "documentation",
            reason="Documents the changed service",
            confidence="medium",
        ),
    )

    report = analyze_completeness(change_set, impact_report)

    assert report.status == "potentially_incomplete"
    assert len(report.affected_and_changed) == 1
    assert report.affected_and_changed[0].path == "tests/test_task_service.py"
    assert len(report.potentially_missing) == 1
    assert report.potentially_missing[0].path == "docs/tasks.md"

    # Both the 'test' (from affected_and_changed) and 'documentation'
    # (from potentially_missing) relationship types must produce recommendations.
    assert "Run related tests" in report.validation_recommendations
    assert "Review affected documentation" in report.validation_recommendations



def _analyze_demo_scenario(
    tmp_path: Path,
    base_revision: str,
    target_revision: str,
):
    repository = Path(__file__).resolve().parents[2]
    scenario_repo = tmp_path / "scenario-repository"

    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            str(repository),
            str(scenario_repo),
        ],
        check=True,
    )

    _git(scenario_repo, "checkout", "-q", target_revision)

    change_set = extract_changed_files(
        str(scenario_repo),
        base_revision,
        target_revision,
    )
    impact_report = discover_relationships(
        str(scenario_repo),
        change_set,
    )

    return change_set, analyze_completeness(
        change_set,
        impact_report,
    )


def test_phase7_scenario_1_is_complete(tmp_path: Path) -> None:
    change_set, report = _analyze_demo_scenario(
        tmp_path,
        "a72fbaa",
        "8f6702a",
    )

    assert [changed.path for changed in change_set.files] == [
        "demo-project/frontend/components/TaskList.jsx",
    ]
    assert report.status == "complete"
    assert report.affected_and_changed == ()
    assert report.potentially_missing == ()
    assert report.validation_recommendations == ()


def test_phase7_scenario_2_detects_missing_get_tasks_consumer(
    tmp_path: Path,
) -> None:
    change_set, report = _analyze_demo_scenario(
        tmp_path,
        "3ae2d52",
        "4e474a2",
    )

    assert [changed.path for changed in change_set.files] == [
        "demo-project/backend/services/task_service.py",
    ]
    assert report.status == "potentially_incomplete"

    assert len(report.potentially_missing) == 1

    missing = report.potentially_missing[0]

    assert missing.path == "demo-project/backend/api/tasks.py"
    assert missing.relationship_types == ("reference",)
    assert missing.reasons == ("References symbol(s): get_tasks",)
    assert missing.confidences == ("medium",)

    assert report.validation_recommendations == ( "Review affected source references", )


def test_phase7_scenario_3_detects_documentation_and_api_collateral(
    tmp_path: Path,
) -> None:
    change_set, report = _analyze_demo_scenario(
        tmp_path,
        "c95f100",
        "4129143",
    )

    assert [changed.path for changed in change_set.files] == [
        "demo-project/backend/api/tasks.py",
    ]
    assert report.status == "potentially_incomplete"

    missing = {
        artifact.path: artifact
        for artifact in report.potentially_missing
    }

        
    assert set(missing) == {
        "README.md",
        "demo-project/backend/main.py",
    }

    assert missing["README.md"].relationship_types == ("documentation",)
    assert missing["README.md"].reasons == (
        "Documentation explicitly references tasks, tasks.py",
    )
    assert missing["README.md"].confidences == ("medium",)

    assert missing["demo-project/backend/main.py"].relationship_types == (
        "reference",
    )
    assert missing["demo-project/backend/main.py"].reasons == (
        "References symbol(s): list_tasks",
    )
    assert missing["demo-project/backend/main.py"].confidences == ("medium",)

    assert report.validation_recommendations == (
        "Review affected documentation",
        "Review affected source references",
    )
