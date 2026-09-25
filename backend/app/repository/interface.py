"""Repository access interfaces reserved for later phases."""

from typing import Protocol


class RepositoryReader(Protocol):
    """Minimal boundary for reading a local repository."""

    def root(self) -> str:
        ...
