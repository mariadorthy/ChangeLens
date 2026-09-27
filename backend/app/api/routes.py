"""FastAPI routes for the ChangeLens analysis workflow."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from analyzer.completeness_analyzer import (
    CompletenessAnalysisError,
    analyze_completeness,
)
from analyzer.git_diff import ChangeDetectionError, extract_changed_files
from analyzer.impact_analyzer import analyze_impact

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request parameters for a repository comparison."""

    repository_path: str | None = Field(default=None)
    repository_url: str | None = Field(default=None)
    base_revision: str = Field(min_length=1)
    target_revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_repository_source(self) -> "AnalyzeRequest":
        if not self.repository_path and not self.repository_url:
            raise ValueError(
                "Provide either repository_path or repository_url."
            )

        if self.repository_url:
            parsed = urlparse(self.repository_url)

            if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
                raise ValueError(
                    "repository_url must be a public GitHub HTTPS URL."
                )

        return self


def _clone_github_repository(repository_url: str) -> Path:
    """Clone a public GitHub repository into a temporary directory."""

    parsed = urlparse(repository_url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError(
            "Only public GitHub HTTPS repositories are supported."
        )

    destination = Path(tempfile.mkdtemp(prefix="changelens-"))

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                repository_url,
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(destination, ignore_errors=True)
        message = exc.stderr.strip() or "GitHub repository could not be cloned."
        raise ValueError(message) from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise ValueError(
            "GitHub repository clone timed out."
        ) from exc

    return destination


def _checkout_revision(repository_path: Path, revision: str) -> None:
    """Check out the requested target revision."""

    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(repository_path),
                "checkout",
                "--quiet",
                "--detach",
                revision,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or f"Git revision '{revision}' was not found."
        raise ValueError(message) from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            f"Checking out revision '{revision}' timed out."
        ) from exc


@router.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    """Run the deterministic Phase 2 → Phase 3 → Phase 4 pipeline."""

    temporary_repository: Path | None = None

    try:
        if request.repository_url:
            temporary_repository = _clone_github_repository(
                request.repository_url
            )
            repository_path = temporary_repository
            _checkout_revision(repository_path, request.target_revision)
        else:
            repository_path = Path(request.repository_path or "").resolve()

            if not repository_path.exists() or not repository_path.is_dir():
                raise ValueError(
                    f"Repository path does not exist: {repository_path}"
                )

        change_set = extract_changed_files(
            str(repository_path),
            request.base_revision,
            request.target_revision,
        )

    except (ChangeDetectionError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_repository_or_revision",
                "message": str(exc),
            },
        ) from exc

    try:
        impact_report = analyze_impact(
            str(repository_path),
            change_set,
        )

        completeness_report = analyze_completeness(
            change_set,
            impact_report,
        )

    except CompletenessAnalysisError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "analysis_failed",
                "message": str(exc),
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "analysis_failed",
                "message": "The analysis pipeline failed.",
            },
        ) from exc

    finally:
        if temporary_repository is not None:
            shutil.rmtree(temporary_repository, ignore_errors=True)

    return completeness_report.to_dict()