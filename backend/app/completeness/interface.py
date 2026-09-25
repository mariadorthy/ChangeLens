"""Completeness analysis boundary reserved for later phases."""

from typing import Protocol


class CompletenessAnalyzer(Protocol):
    """Future interface for comparing affected artifacts with actual changes."""

    def find_missing_work(self, affected_artifacts: list[object], changed_files: list[str]) -> list[object]:
        ...
