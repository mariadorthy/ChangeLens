# Analyzer

The analyzer package contains the repository/change-analysis boundaries used by ChangeLens.

## Phase 2: Change Detection Engine

`analyzer.git_diff` now implements deterministic Git revision comparison. It accepts a repository path plus two explicit Git revisions and returns a structured `ChangeSet` containing:

- repository path
- resolved base and target commit IDs
- changed files
- `added`, `modified`, `deleted`, and Git-detected `renamed` statuses
- additions and deletions
- hunk locations (`old_start`, `old_count`, `new_start`, `new_count`)
- added and removed lines for each changed file

Example:

```python
from analyzer.git_diff import extract_changed_files

result = extract_changed_files("/path/to/repository", "HEAD~1", "HEAD")
print(result.to_dict())
```

The implementation uses the Git CLI through Python's standard library; no new dependency is required.

## Error handling

Invalid repository paths, unavailable Git, invalid revisions, and invalid Git operations raise `ChangeDetectionError` with a useful message. The detector does not silently turn invalid input into an empty change set.

## Current limitations

- The Phase 2 API compares two explicit revisions. Working-tree baseline detection is intentionally deferred.
- Rename detection relies on Git's standard rename detection (`-M`); Git may classify ambiguous cases differently.
- Unsupported Git status codes are safely represented as `modified` rather than crashing.
- Phase 3 relationship discovery is deterministic and evidence-based; it does not decide whether a related artifact actually needs a change.
- Phase 3 does not perform completeness analysis, ranking, AI/LLM analysis, GitHub integration, autonomous modification, or final report generation.

## Phase 3: Repository Relationship / Impact Discovery

`analyzer.impact_analyzer` consumes the Phase 2 `ChangeSet` and discovers deterministic, evidence-backed relationships between changed files and other repository artifacts.

Example:

```python
from analyzer.git_diff import extract_changed_files
from analyzer.impact_analyzer import discover_relationships

changes = extract_changed_files(
    "/path/to/repository",
    "HEAD~1",
    "HEAD",
)

report = discover_relationships(
    "/path/to/repository",
    changes,
)

print(report.to_dict())