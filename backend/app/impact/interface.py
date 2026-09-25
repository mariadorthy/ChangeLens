"""Impact analysis boundary reserved for later phases."""

from typing import Protocol


class ImpactAnalyzer(Protocol):
    """Future interface for identifying potentially affected artifacts."""

    def analyze(self, changed_files: list[str]) -> list[object]:
        ...
