# Analyzer

The `analyzer` package contains the core deterministic analysis components used by ChangeLens.

It is responsible for:

1. detecting changes between Git revisions
2. discovering relationships between changed files and repository artifacts
3. evaluating whether related artifacts were also changed
4. producing structured evidence for the final analysis report

---

## Analysis Flow

```text
Git Revisions
      ↓
Git Diff
      ↓
ChangeSet
      ↓
Relationship Discovery
      ↓
Completeness Analysis
      ↓
Analysis Report
```


## Git Diff

The `analyzer.git_diff` package compares two explicit Git revisions and produces a structured `ChangeSet`.

It captures:

* repository path
* resolved base and target revisions
* changed files
* added files
* modified files
* deleted files
* Git-detected renames
* additions and deletions
* changed hunk locations
* added and removed lines

Example:

```python
from analyzer.git_diff import extract_changed_files

result = extract_changed_files(
    "/path/to/repository",
    "HEAD~1",
    "HEAD",
)

print(result.to_dict())
```

The implementation uses the Git CLI through Python's standard library.

No additional dependency is required for Git change detection.

---

## Relationship Discovery

The `analyzer.impact_analyzer` package examines repository artifacts related to the detected changes.

The current implementation supports deterministic relationships including:

* Python imports
* JavaScript imports
* API consumers
* references to changed Python symbols
* tests
* documentation
* configuration
* explicit file references
* environment-variable references

Relationships include evidence and confidence information where applicable.

The analyzer reports relationships that may require attention. It does not assume that every relationship necessarily requires a code or documentation change.

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
```

---

## Completeness Analysis

The completeness analysis combines:

* the detected `ChangeSet`
* discovered relationships
* the files included in the detected change

It separates related artifacts into concepts such as:

* changed
* affected and changed
* potentially missing

A potentially missing artifact is not automatically considered incorrect or definitely required to change.

The finding means that the analyzer discovered a relationship that may require developer review.

---

## Error Handling

The Git change detection layer reports errors for conditions such as:

* invalid repository paths
* unavailable Git
* invalid revisions
* invalid Git operations

Invalid input is not silently converted into an empty change set.

---

## Deterministic Analysis

The analyzer is intentionally deterministic.

It does not currently use:

* LLM analysis
* generative AI
* autonomous code modification
* GitHub integration
* cloud services
* external paid APIs

The analyzer reports evidence discovered from the repository rather than inventing relationships or required changes.

---

## Historical Analysis

Relationship discovery examines the repository filesystem available to the analyzer.

For historical Git scenarios, the repository should therefore be checked out at the target revision before running the analysis.

Clean Git worktrees are used by the verified demo scenarios to preserve reproducibility.

---

## Testing

The analyzer is covered by the project's automated test suite.

The latest verified backend/analyzer test result is:

```text
40 passed, 1 pre-existing deprecation warning
```

The warning is an existing Starlette/httpx deprecation warning and does not currently cause test failure.

---

## Scope

The analyzer is intentionally focused on deterministic repository change and relationship analysis.

The current project does not include:

* remote GitHub repository analysis
* authentication
* deployment infrastructure
* autonomous code modification
* full semantic program analysis
* guaranteed detection of every possible dependency