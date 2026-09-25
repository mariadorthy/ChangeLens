"""Public boundary for ChangeLens Phase 4 completeness analysis."""

from .service import (
    COMPLETENESS_STATUSES,
    CompletenessAnalysisError,
    CompletenessArtifact,
    CompletenessReport,
    analyze_completeness,
    find_missing_work,
)

__all__ = [
    "COMPLETENESS_STATUSES",
    "CompletenessAnalysisError",
    "CompletenessArtifact",
    "CompletenessReport",
    "analyze_completeness",
    "find_missing_work",
]