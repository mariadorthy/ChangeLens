from dataclasses import asdict, dataclass


@dataclass
class Task:
    id: int
    title: str
    completed: bool

    def to_dict(self) -> dict:
        """Return the task as a JSON-ready dictionary."""
        return asdict(self)