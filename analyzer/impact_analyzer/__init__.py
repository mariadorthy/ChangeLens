"""Public boundary for ChangeLens Phase 3 relationship discovery."""

from .service import (
    ImpactDiscoveryError,
    ImpactReport,
    ImpactResult,
    Relationship,
    analyze_impact,
    discover_relationships,
)

__all__ = [
    "ImpactDiscoveryError",
    "ImpactReport",
    "ImpactResult",
    "Relationship",
    "analyze_impact",
    "discover_relationships",
]