from dataclasses import asdict, dataclass


@dataclass
class Task:
    id: int
    title: str
    completed: bool

    def to_dict(self) -> dict:
        return asdict(self)
