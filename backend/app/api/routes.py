"""FastAPI routes for the ChangeLens analysis workflow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from analyzer.completeness_analyzer import (
    CompletenessAnalysisError,
    analyze_completeness,
)
from analyzer.git_diff import ChangeDetectionError, extract_changed_files
from analyzer.impact_analyzer import analyze_impact


router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request parameters for a repository comparison."""

    repository_path: str = Field(min_length=1)
    base_revision: str = Field(min_length=1)
    target_revision: str = Field(min_length=1)


@router.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    """Run the deterministic Phase 2 → Phase 3 → Phase 4 pipeline."""

    try:
        change_set = extract_changed_files(
            request.repository_path,
            request.base_revision,
            request.target_revision,
        )
    except ChangeDetectionError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_repository_or_revision",
                "message": str(exc),
            },
        ) from exc

    try:
        impact_report = analyze_impact(
            request.repository_path,
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

    return completeness_report.to_dict()
