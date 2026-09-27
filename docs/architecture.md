# ChangeLens Architecture

ChangeLens separates Git change extraction, repository relationship discovery, completeness analysis, API orchestration, and the developer-facing dashboard.

The implemented flow is:

```text
Git Repository
      ↓
Base Revision + Target Revision
      ↓
Git Diff Engine
      ↓
Structured ChangeSet
      ↓
Impact / Relationship Analyzer
      ↓
Evidence-backed Relationships
      ↓
Completeness Analyzer
      ↓
Analysis Report
      ↓
FastAPI /analyze
      ↓
React + Vite Dashboard
```

## Components

### Git Diff Engine

The `analyzer.git_diff` package is responsible for factual Git change extraction.

It identifies:

* file status
* file paths
* additions
* deletions
* changed hunks
* changed lines
* Git-detected renames

The output is represented as a structured `ChangeSet`.

The Git diff layer does not determine whether a related file needs to change.

---

### Impact / Relationship Analyzer

The `analyzer.impact_analyzer` package consumes the `ChangeSet` and examines repository artifacts for evidence-backed relationships.

Current relationship discovery includes:

* Python imports
* JavaScript imports
* API consumers
* tests
* documentation
* configuration references
* explicit file references
* environment-variable references
* source references to changed Python symbols

Each discovered relationship can carry:

* relationship type
* evidence
* confidence

The analyzer identifies potential relationships; it does not independently declare that every relationship requires a code change.

---

### Completeness Analyzer

The `analyzer.completeness_analyzer` package combines the Git change set and discovered relationships.

It distinguishes:

```text
Changed
Affected & Changed
Potentially Missing
```

A potentially incomplete result is produced when related artifacts are discovered but were not included in the detected change.

Recommendations are generated deterministically from the discovered relationships.

---

### FastAPI Backend

The backend provides the application boundary between the analysis engine and the frontend.

The main endpoints are:

```text
GET  /health
POST /analyze
```

`POST /analyze` accepts:

```text
repository_path
base_revision
target_revision
```

and executes:

```text
Git Diff
→ Impact Analysis
→ Completeness Analysis
```

The API returns the resulting analysis report to the dashboard.

Invalid repository or revision input is reported as a client error, while unexpected analysis failures are handled as server errors without exposing internal exception details.

---

### React Dashboard

The frontend is implemented with React and Vite.

It provides:

* repository path input
* base revision input
* target revision input
* analysis execution
* loading state
* error state
* result status
* changed-file display
* affected-and-changed display
* potentially-missing display
* relationship evidence
* confidence
* validation recommendations
* reset/run-another-analysis workflow

The dashboard consumes the FastAPI analysis response rather than implementing the repository analysis itself.

---

## Data Flow

A normal analysis follows this sequence:

```text
1. User enters repository path and two Git revisions.
                         ↓
2. FastAPI validates the request.
                         ↓
3. Git Diff Engine extracts the factual ChangeSet.
                         ↓
4. Impact Analyzer discovers repository relationships.
                         ↓
5. Completeness Analyzer compares relationships with
   the detected change.
                         ↓
6. Analysis report is serialized by the backend.
                         ↓
7. React dashboard renders the report.
```

---

## Evidence Model

ChangeLens intentionally separates detected facts from recommendations.

For example:

```text
Relationship:
reference

Evidence:
References symbol(s): get_tasks

Confidence:
medium
```

This allows the developer to see why an artifact was surfaced rather than receiving an unexplained recommendation.

The term **potentially missing** is therefore deliberate. A relationship indicates that an artifact may deserve review; it does not prove that the artifact must be modified.

---

## Historical Reproducibility

The relationship analyzer examines files available in the repository filesystem.

Git revision comparison alone does not automatically replace the filesystem with the historical target revision.

Therefore, historical demo scenarios should be executed from clean worktrees or clones at the relevant target revision.

This prevents later files in the current working tree from introducing additional relationships into a historical scenario.

The three verified demo scenarios use:

```text
Scenario 1
a72fbaa → 8f6702a

Scenario 2
3ae2d52 → 4e474a2

Scenario 3
c95f100 → 4129143
```

and were verified using clean target-revision worktrees.

---

## Verification

The current verified project state includes:

Run from the repository root using the backend virtual environment:

```powershell
.\backend\venv\Scripts\python.exe -m pytest -q
```

```text
40 passed, 1 pre-existing deprecation warning
```

```powershell
cd frontend
npm test
```

```text
9 tests passed
```

```powershell
cd frontend
npm run build
```

```text
successful
```

The remaining warning is a pre-existing Starlette/httpx deprecation warning and does not represent a failing test.

---

## Scope

ChangeLens is intentionally focused on local developer workflow analysis.

The current implementation does not include:

* remote GitHub repository integration
* authentication
* deployment infrastructure
* LLM-based analysis
* autonomous code modification
* production database infrastructure

The architecture is designed around small, testable deterministic components that can be extended later without changing the core workflow.
