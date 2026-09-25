"""Deterministic change completeness analysis for ChangeLens Phase 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from analyzer.git_diff import ChangeSet, ChangedFile
from analyzer.impact_analyzer import ImpactReport, Relationship


COMPLETENESS_STATUSES = {
    "complete",
    "potentially_incomplete",
}

_RECOMMENDATIONS = {
    "test": "Run related tests",
    "api_consumer": "Validate API consumers",
    "configuration": "Validate configuration-dependent behavior",
    "documentation": "Review affected documentation",
    "import": "Run affected module tests",
    "reference": "Review affected source references",
}


@dataclass(frozen=True)
class CompletenessArtifact:
    """An artifact involved in the completeness assessment."""

    path: str
    relationship_types: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    confidences: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompletenessReport:
    """Structured Phase 4 completeness result."""

    status: str
    changed_files: tuple[str, ...]
    affected_and_changed: tuple[CompletenessArtifact, ...]
    potentially_missing: tuple[CompletenessArtifact, ...]
    validation_recommendations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "changed_files": list(self.changed_files),
            "affected_and_changed": [
                artifact.to_dict()
                for artifact in self.affected_and_changed
            ],
            "potentially_missing": [
                artifact.to_dict()
                for artifact in self.potentially_missing
            ],
            "validation_recommendations": list(
                self.validation_recommendations
            ),
        }


class CompletenessAnalysisError(RuntimeError):
    """Raised when completeness analysis cannot process its inputs."""


def _normalise_path(path: str) -> str:
    """Return a repository-relative path in canonical form."""
    return path.replace("\\", "/").lstrip("./")


def _changed_paths(change_set: ChangeSet) -> set[str]:
    """Return all paths represented by the ChangeSet."""
    paths: set[str] = set()

    for changed_file in change_set.files:
        paths.add(_normalise_path(changed_file.path))

        if changed_file.old_path:
            paths.add(_normalise_path(changed_file.old_path))

    return paths


def _active_changed_paths(change_set: ChangeSet) -> set[str]:
    """Return paths that exist as changed artifacts at the target."""
    paths: set[str] = set()

    for changed_file in change_set.files:
        path = _normalise_path(changed_file.path)

        if changed_file.status != "deleted":
            paths.add(path)

    return paths


def _relationship_artifact(
    path: str,
    relationships: list[Relationship],
) -> CompletenessArtifact:
    """Aggregate all relationships for one repository artifact."""
    relationship_types = tuple(
        sorted({relationship.type for relationship in relationships})
    )
    reasons = tuple(
        sorted(
            {
                relationship.reason
                for relationship in relationships
                if relationship.reason
            }
        )
    )
    confidences = tuple(
        sorted({relationship.confidence for relationship in relationships})
    )

    return CompletenessArtifact(
        path=path,
        relationship_types=relationship_types,
        reasons=reasons,
        confidences=confidences,
    )


def _recommendations(
    artifacts: tuple[CompletenessArtifact, ...],
) -> tuple[str, ...]:
    """Create deterministic validation recommendations."""
    recommendations: set[str] = set()

    for artifact in artifacts:
        for relationship_type in artifact.relationship_types:
            recommendation = _RECOMMENDATIONS.get(relationship_type)
            if recommendation:
                recommendations.add(recommendation)

    return tuple(sorted(recommendations))


def analyze_completeness(
    change_set: ChangeSet,
    impact_report: ImpactReport,
) -> CompletenessReport:
    """Compare Phase 2 changes with Phase 3 relationships."""
    changed_paths = _changed_paths(change_set)
    active_changed_paths = _active_changed_paths(change_set)

    changed_files = tuple(
        _normalise_path(changed_file.path)
        for changed_file in change_set.files
    )

    affected_by_path: dict[str, list[Relationship]] = {}

    for impact_result in impact_report.changed_files:
        for relationship in impact_result.relationships:
            path = _normalise_path(relationship.path)
            affected_by_path.setdefault(path, []).append(relationship)

    affected_and_changed: list[CompletenessArtifact] = []
    potentially_missing: list[CompletenessArtifact] = []

    for path in sorted(affected_by_path):
        relationships = affected_by_path[path]

        if path in active_changed_paths:
            affected_and_changed.append(
                _relationship_artifact(path, relationships)
            )
            continue

        # A deleted or renamed-away path is not treated as missing work.
        if any(
            changed_file.status == "deleted"
            and _normalise_path(changed_file.path) == path
            for changed_file in change_set.files
        ):
            continue

        if any(
            changed_file.status == "renamed"
            and changed_file.old_path
            and _normalise_path(changed_file.old_path) == path
            for changed_file in change_set.files
        ):
            continue

        potentially_missing.append(
            _relationship_artifact(path, relationships)
        )

    # Keep the ChangeSet as the source of truth for changed artifacts.
    # The variable is intentionally computed above so old paths are recognized
    # during rename/delete handling without being reported as missing work.
    _ = changed_paths

    missing_tuple = tuple(potentially_missing)
    status = (
        "potentially_incomplete"
        if missing_tuple
        else "complete"
    )

    return CompletenessReport(
        status=status,
        changed_files=changed_files,
        affected_and_changed=tuple(affected_and_changed),
        potentially_missing=missing_tuple,
        validation_recommendations=_recommendations(missing_tuple),
    )


def find_missing_work(
    change_set: ChangeSet,
    impact_report: ImpactReport,
) -> CompletenessReport:
    """Phase 4 public compatibility entry point."""
    return analyze_completeness(change_set, impact_report)