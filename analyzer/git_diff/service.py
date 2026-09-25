"""Git revision comparison for the ChangeLens change-detection engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import re
import subprocess
from typing import Any


class ChangeDetectionError(RuntimeError):
    """Raised when a repository or Git revision cannot be inspected."""


@dataclass(frozen=True)
class DiffHunk:
    """Location of one changed hunk in the old and new files."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int


@dataclass(frozen=True)
class ChangedFile:
    """Structured information about one file changed between two revisions."""

    path: str
    status: str
    old_path: str | None
    additions: int
    deletions: int
    hunks: tuple[DiffHunk, ...]
    added_lines: tuple[str, ...] = ()
    removed_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeSet:
    """Complete deterministic result for a two-revision Git comparison."""

    repository: str
    base_revision: str
    target_revision: str
    files: tuple[ChangedFile, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for future API consumers."""
        return asdict(self)


_HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


def _run_git(repository: str, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise ChangeDetectionError("Git executable is not available on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "Git command failed").strip()
        raise ChangeDetectionError(detail) from exc
    return completed.stdout


def _validate_repository(repository_path: str) -> str:
    repository = os.path.abspath(repository_path)
    if not os.path.isdir(repository):
        raise ChangeDetectionError(f"Repository path does not exist or is not a directory: {repository}")
    try:
        git_dir = _run_git(repository, ["rev-parse", "--git-dir"]).strip()
    except ChangeDetectionError as exc:
        raise ChangeDetectionError(f"Not a Git repository: {repository}") from exc
    if not git_dir:
        raise ChangeDetectionError(f"Not a Git repository: {repository}")
    return repository


def _validate_revision(repository: str, revision: str, label: str) -> str:
    if not revision.strip():
        raise ChangeDetectionError(f"{label} revision must not be empty")
    try:
        return _run_git(repository, ["rev-parse", "--verify", f"{revision}^{{commit}}"]).strip()
    except ChangeDetectionError as exc:
        raise ChangeDetectionError(f"Invalid {label} revision: {revision}") from exc


def _parse_name_status(output: str) -> list[tuple[str, str, str | None]]:
    records = output.split("\0")
    changes: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(records) - 1:
        status = records[index]
        index += 1
        if not status:
            continue
        code = status[0]
        if code in {"R", "C"}:
            if index + 1 >= len(records):
                raise ChangeDetectionError("Git returned an incomplete rename/copy status")
            old_path = records[index]
            new_path = records[index + 1]
            index += 2
            changes.append(("renamed" if code == "R" else "modified", new_path, old_path))
        else:
            if index >= len(records):
                raise ChangeDetectionError("Git returned an incomplete file status")
            path = records[index]
            index += 1
            mapped = {"A": "added", "M": "modified", "D": "deleted"}.get(code, "modified")
            changes.append((mapped, path, None))
    return changes


def _parse_patch(patch: str) -> tuple[int, int, tuple[DiffHunk, ...], tuple[str, ...], tuple[str, ...]]:
    additions = 0
    deletions = 0
    hunks: list[DiffHunk] = []
    added_lines: list[str] = []
    removed_lines: list[str] = []

    for line in patch.splitlines():
        match = _HUNK_RE.match(line)
        if match:
            hunks.append(
                DiffHunk(
                    old_start=int(match.group(1)),
                    old_count=int(match.group(2) or "1"),
                    new_start=int(match.group(3)),
                    new_count=int(match.group(4) or "1"),
                )
            )
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
            added_lines.append(line[1:])
        elif line.startswith("-"):
            deletions += 1
            removed_lines.append(line[1:])

    return additions, deletions, tuple(hunks), tuple(added_lines), tuple(removed_lines)


def extract_changed_files(
    repository_path: str,
    base_revision: str,
    target_revision: str,
) -> ChangeSet:
    """Compare two Git revisions and return their structured file-level changes.

    Git's rename detector is enabled at its default threshold. Unsupported Git
    status codes are represented safely as ``modified`` rather than causing the
    detector to crash.
    """
    repository = _validate_repository(repository_path)
    base = _validate_revision(repository, base_revision, "base")
    target = _validate_revision(repository, target_revision, "target")

    status_output = _run_git(
        repository,
        ["diff", "--name-status", "-z", "-M", base, target, "--"],
    )
    statuses = _parse_name_status(status_output)
    files: list[ChangedFile] = []

    for status, path, old_path in statuses:
        patch = _run_git(
            repository,
            ["diff", "--no-ext-diff", "--unified=0", "-M", base, target, "--", *( [old_path, path] if old_path else [path] )],
        )
        additions, deletions, hunks, added_lines, removed_lines = _parse_patch(patch)
        files.append(
            ChangedFile(
                path=path,
                status=status,
                old_path=old_path,
                additions=additions,
                deletions=deletions,
                hunks=hunks,
                added_lines=added_lines,
                removed_lines=removed_lines,
            )
        )

    return ChangeSet(
        repository=repository,
        base_revision=base,
        target_revision=target,
        files=tuple(files),
    )
