"""Public boundary for the ChangeLens Git change-detection engine."""

from .service import ChangeDetectionError, ChangeSet, ChangedFile, DiffHunk, extract_changed_files

__all__ = [
    "ChangeDetectionError",
    "ChangeSet",
    "ChangedFile",
    "DiffHunk",
    "extract_changed_files",
]
