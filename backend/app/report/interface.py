"""Report generation boundary reserved for later phases."""

from typing import Protocol


class ReportGenerator(Protocol):
    """Future interface for rendering evidence-backed analysis results."""

    def generate(self, findings: list[object]) -> object:
        ...
