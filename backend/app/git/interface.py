"""Git integration boundary reserved for later phases."""

from typing import Protocol


class GitChangeReader(Protocol):
    """Boundary for obtaining a change set from Git."""

    def changed_files(self) -> list[str]:
        ...
