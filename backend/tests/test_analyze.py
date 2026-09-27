from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app

from unittest.mock import patch

import backend.app.api.routes as routes

client = TestClient(app)


def _run_git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write(repository: Path, relative_path: str, contents: str) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _init_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repo"
    repository.mkdir()

    _run_git(repository, "init")
    _run_git(repository, "config", "user.email", "test@example.com")
    _run_git(repository, "config", "user.name", "ChangeLens Test")

    return repository


def _commit(repository: Path, message: str) -> str:
    _run_git(repository, "add", ".")
    _run_git(repository, "commit", "-m", message)
    return _run_git(repository, "rev-parse", "HEAD")


def test_analyze_valid_repository_returns_complete_report(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path)

    _write(
        repository,
        "README.md",
        "ChangeLens test repository\n",
    )
    base_revision = _commit(repository, "base")

    _write(
        repository,
        "README.md",
        "ChangeLens updated repository\n",
    )
    target_revision = _commit(repository, "target")

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": base_revision,
            "target_revision": target_revision,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "complete"
    assert body["changed_files"] == ["README.md"]
    assert body["affected_and_changed"] == []
    assert body["potentially_missing"] == []
    assert body["validation_recommendations"] == []


def test_analyze_detects_potentially_missing_related_artifact(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path)

    _write(
        repository,
        "backend/services/task_service.py",
        """def get_tasks() -> list[str]:
    return ["task"]
""",
    )
    _write(
        repository,
        "backend/api/tasks.py",
        """from backend.services.task_service import get_tasks


def list_tasks() -> list[str]:
    return get_tasks()
""",
    )

    base_revision = _commit(repository, "base")

    _write(
        repository,
        "backend/services/task_service.py",
        """def get_tasks() -> list[str]:
    return ["updated-task"]
""",
    )
    target_revision = _commit(repository, "target")

    head_before = _run_git(repository, "rev-parse", "HEAD")

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": base_revision,
            "target_revision": target_revision,
        },
    )

    head_after = _run_git(repository, "rev-parse", "HEAD")

    assert response.status_code == 200
    assert head_before == head_after

    body = response.json()

    assert body["status"] == "potentially_incomplete"

    missing_paths = {
        artifact["path"]
        for artifact in body["potentially_missing"]
    }

    assert "backend/api/tasks.py" in missing_paths


def test_analyze_rejects_invalid_repository(tmp_path: Path) -> None:
    repository = tmp_path / "does-not-exist"

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": "HEAD",
            "target_revision": "HEAD",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["detail"]["code"] == "invalid_repository_or_revision"
    assert "Repository path" in body["detail"]["message"]


def test_analyze_rejects_invalid_revision(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path)

    _write(repository, "README.md", "initial\n")
    base_revision = _commit(repository, "base")

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": base_revision,
            "target_revision": "does-not-exist",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["detail"]["code"] == "invalid_repository_or_revision"
    assert "Invalid target revision" in body["detail"]["message"]


def test_analyze_rejects_missing_request_data() -> None:
    response = client.post("/analyze", json={})

    assert response.status_code == 422

    body = response.json()

    assert body["detail"]

    fields = {
        error["loc"][-1]
        for error in body["detail"]
    }

    assert fields == {
        "base_revision",
        "target_revision",
    }

def test_health_returns_readiness_response() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "changelens-backend",
    }


def test_analyze_rejects_invalid_base_revision(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path)

    _write(repository, "README.md", "initial\n")
    target_revision = _commit(repository, "base")

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": "does-not-exist",
            "target_revision": target_revision,
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["detail"]["code"] == "invalid_repository_or_revision"
    assert "Invalid base revision" in body["detail"]["message"]


def test_analyze_same_revision_returns_complete_empty_change_set(
    tmp_path: Path,
) -> None:
    repository = _init_repository(tmp_path)

    _write(repository, "README.md", "initial\n")
    revision = _commit(repository, "base")

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
            "base_revision": revision,
            "target_revision": revision,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "complete"
    assert body["changed_files"] == []
    assert body["affected_and_changed"] == []
    assert body["potentially_missing"] == []
    assert body["validation_recommendations"] == []

def test_analyze_hides_unexpected_pipeline_errors(tmp_path: Path) -> None:
    repository = _init_repository(tmp_path)

    _write(repository, "README.md", "initial\n")
    base_revision = _commit(repository, "base")

    _write(repository, "README.md", "updated\n")
    target_revision = _commit(repository, "target")

    with patch.object(
    routes,
    "analyze_impact",
    side_effect=RuntimeError("secret internal failure"),
):
        response = client.post(
            "/analyze",
            json={
                "repository_path": str(repository),
                "base_revision": base_revision,
                "target_revision": target_revision,
            },
        )

    assert response.status_code == 500

    body = response.json()

    assert body["detail"] == {
        "code": "analysis_failed",
        "message": "The analysis pipeline failed.",
    }
    assert "secret internal failure" not in response.text