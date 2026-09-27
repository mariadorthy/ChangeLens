# ChangeLens

> **Know what else needs to change.**

We built ChangeLens as a developer workflow tool to answer a practical question:

> **“I changed this code — what else do I need to update?”**

Instead of only showing which files changed between two Git revisions, ChangeLens discovers related repository artifacts and identifies relationships that may require follow-up attention.

## Demo Video

🎥 **ChangeLens Demo:** [Watch the 2-3 minute demo video](https://canva.link/1f4i04vwug4stfc)

The video demonstrates the complete ChangeLens workflow:
change detection → relationship discovery → completeness analysis → developer action.

---

## Problem

A code change rarely exists in isolation.

Changing a source file can affect:

* other source files
* API consumers
* tests
* documentation
* configuration
* explicit symbol references

A normal Git diff answers:

> **What changed?**

But developers also need to consider:

> **What else may need attention because of that change?**

We focus on that second question with ChangeLens.

It does not claim that every discovered relationship requires a modification. Instead, it provides evidence-backed findings that help developers review potentially affected work.

---

## Solution

We compare two Git revisions and process the change through a deterministic analysis pipeline:

```text
Git Diff
   ↓
Relationship Discovery
   ↓
Completeness Analysis
   ↓
Actionable Report
```

The result separates three useful concepts:

### Changed

Files directly modified between the selected Git revisions.

### Affected & Changed

Related artifacts that were also included in the detected change.

### Potentially Missing

Related artifacts discovered by the analyzer that were not included in the detected change.

> **“Potentially missing” means the analyzer found a relationship that may require attention; it does not mean the artifact is definitely incorrect or definitely required to change.**

Each relationship can include evidence, relationship type, and confidence to make the finding reviewable.

---

## How It Works

```text
Git Repository
      ↓
Git Diff Engine
      ↓
Impact / Relationship Analyzer
      ↓
Completeness Analyzer
      ↓
FastAPI /analyze
      ↓
React Dashboard
```

### 1. Git Diff Engine

The Git diff layer compares the requested base and target revisions.

It identifies:

* added files
* modified files
* deleted files
* Git-detected renames
* additions and deletions
* changed hunks and lines

The result is represented as a structured `ChangeSet`.

### 2. Impact / Relationship Analyzer

The relationship analyzer examines repository artifacts and looks for evidence-backed relationships involving changed files.

The current implementation covers relationships including:

* Python imports
* JavaScript imports
* API consumers
* source references to changed Python symbols
* tests
* documentation
* configuration
* explicit file references
* environment-variable references

The analyzer records relationship evidence and confidence rather than treating every relationship as a guaranteed required change.

### 3. Completeness Analyzer

The completeness layer combines the detected change set and discovered relationships.

It determines whether related artifacts were also changed or whether related artifacts remain potentially missing.

Recommendations are generated deterministically from the relationships discovered by the analyzer.

### 4. FastAPI Backend

The backend exposes the analysis workflow through:

```text
POST /analyze
```

and provides a lightweight health endpoint:

```text
GET /health
```

The API validates repository/revision input and returns structured analysis results.

### 5. React Dashboard

The frontend provides the developer-facing workflow for entering:

```text
Repository Path
Base Revision
Target Revision
```

and displaying:

* analysis status
* changed files
* affected & changed artifacts
* potentially missing artifacts
* relationship evidence
* confidence
* validation recommendations

---

## Architecture

```text
                         ChangeLens
                            │
                            ▼
                    Git Repository
                            │
                    Base + Target Revision
                            │
                            ▼
                    ┌───────────────┐
                    │ Git Diff      │
                    │ Engine        │
                    └───────┬───────┘
                            │
                       ChangeSet
                            │
                            ▼
                    ┌───────────────┐
                    │ Impact /      │
                    │ Relationship  │
                    │ Analyzer      │
                    └───────┬───────┘
                            │
                   Evidence-backed
                    relationships
                            │
                            ▼
                    ┌───────────────┐
                    │ Completeness  │
                    │ Analyzer      │
                    └───────┬───────┘
                            │
                     Analysis Report
                            │
                            ▼
                    ┌───────────────┐
                    │ FastAPI        │
                    │ /analyze       │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ React + Vite   │
                    │ Dashboard      │
                    └───────────────┘
```

---

## Demo Scenarios

We prepared three deterministic Git scenarios using real revisions from the project history.

### Scenario 1 — Complete

**Purpose:** Demonstrate a change with no potentially missing related artifacts.

```text
Base:   a72fbaa
Target: 8f6702a
```

Changed:

```text
demo-project/frontend/components/TaskList.jsx
```

Result:

```text
Complete
```

Potentially missing:

```text
0
```

Affected & changed:

```text
0
```

This demonstrates the positive case where the detected change has no additional related artifact requiring attention.

---

### Scenario 2 — Potentially Incomplete

**Purpose:** Demonstrate a source change whose related consumer was not included.

```text
Base:   3ae2d52
Target: 4e474a2
```

Changed:

```text
demo-project/backend/services/task_service.py
```

Potentially missing:

```text
demo-project/backend/api/tasks.py
```

Relationship:

```text
reference
```

Evidence:

```text
References symbol(s): get_tasks
```

Confidence:

```text
medium
```

Recommendation:

```text
Review affected source references
```

Final status:

```text
potentially_incomplete
```

---

### Scenario 3 — Hidden Collateral Dependency

**Purpose:** Demonstrate that a changed API artifact can have both source and documentation relationships that also need review.

```text
Base:   c95f100
Target: 4129143
```

Changed:

```text
demo-project/backend/api/tasks.py
```

Potentially missing:

```text
README.md
demo-project/backend/main.py
```

Relationships:

```text
README.md
→ documentation

demo-project/backend/main.py
→ reference
```

Evidence:

```text
README.md
→ Documentation explicitly references tasks, tasks.py

demo-project/backend/main.py
→ References symbol(s): list_tasks
```

Confidence:

```text
medium
```

Recommendations:

```text
Review affected documentation
Review affected source references
```

Final status:

```text
potentially_incomplete
```

---

## Reproducing the Demo

Historical scenarios should be analyzed from clean target-revision worktrees.

This is important because the relationship analyzer examines files available in the repository filesystem. Running an historical comparison against a later working tree can introduce relationships from files that did not exist at the historical target revision.

### Create clean scenario worktrees

From the parent directory of the repository:

```powershell
git worktree add ..\changelens-s1 8f6702a
git worktree add ..\changelens-s2 4e474a2
git worktree add ..\changelens-s3 4129143
```

Do not reset or clean the main working tree.

### Start the backend

From the ChangeLens repository:

```powershell
uvicorn backend.app.main:app --reload
```

The backend runs on the local FastAPI development server.

### Start the frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

### Run an analysis

Enter:

```text
Repository Path
Base Revision
Target Revision
```

Then select **Analyze Changes**.

For the three preserved scenarios, use the revision pairs documented above.

---

## Running ChangeLens

### Prerequisites

* Python 3.10+
* Node.js 18+
* npm
* Git

No cloud service or paid API is required.

### Backend dependencies

The backend requirements include:

* FastAPI
* Uvicorn
* pytest
* httpx

Install them in the Python environment used for the project:

```powershell
pip install -r backend\requirements.txt
```

### Frontend dependencies

From `frontend/`:

```powershell
npm install
```

---

## Testing

The latest verified project state is:

### Backend and analyzer

Run from the repository root using the backend virtual environment:

```powershell
.\backend\venv\Scripts\python.exe -m pytest -q
```

Expected output:

```text
40 passed, 1 pre-existing deprecation warning
```

### Frontend

```text
npm test
9 tests passed
```

### Production build

```text
npm run build
successful
```

The backend test run reports one pre-existing Starlette/httpx deprecation warning. The tests themselves pass.

The test suite covers change detection, relationship discovery, completeness behavior, API behavior, error handling, edge cases, frontend behavior, and the three deterministic demo scenarios.

---

## Project Structure

```text
change-completeness-analyzer/
├── analyzer/              # Git, impact, and completeness analysis
├── backend/               # FastAPI application
├── frontend/              # React + Vite dashboard
├── demo-project/          # Deterministic task-management fixture
├── tests/                 # Additional test area
├── docs/                  # Project documentation
├── bob_sessions/          # IBM Bob session reports and evidence
├── .env.example           # Local environment template
├── .gitignore
├── AGENTS.md              # Development rules
├── LICENSE
└── README.md
```

---

## Technology

ChangeLens currently uses:

* Python
* FastAPI
* Uvicorn
* React
* Vite
* Vitest
* Git
* deterministic/static repository analysis

---

## Known Limitations

We intentionally kept ChangeLens focused on a local, deterministic MVP.

Known limitations include:

* Relationship discovery is deterministic/static analysis rather than full semantic understanding.
* Confidence values are heuristic indicators produced by the analyzer.
* A `potentially missing` finding does not prove that a file must be changed.
* Relationship discovery examines the repository filesystem available to the analyzer.
* Historical Git scenarios therefore require clean target-revision worktrees for reproducible results.
* The current workflow requires access to a local Git repository.
* Remote GitHub repository analysis is not implemented.
* Ambiguous or unsupported code patterns may not be detected.
* No authentication, deployment infrastructure, or cloud service is required or included.

---

## Environment

The repository includes `.env.example` as the documented location for future local configuration.

The current implementation does not require environment variables or secrets to run the core workflow.

Do not commit local `.env` files or secrets.

---

## IBM Bob

IBM Bob 2.0 was used as a genuine development and verification assistant
throughout the ChangeLens workflow.

Our use of IBM Bob covered four connected areas:

* **Repository review** — understanding the existing architecture, repository
  structure, relationships, and implementation before making changes
* **Testing and verification** — identifying regression gaps, reviewing edge
  cases, and validating behavior with the existing test suite
* **Focused development** — implementing targeted improvements supported by
  repository findings and adding regression coverage
* **Documentation and submission review** — reviewing documentation,
  repository hygiene, evidence organization, and final submission readiness

### Member 1 — Engineering workflow

Member 1 used IBM Bob for:

1. Repository and architecture orientation
2. Testing and regression analysis
3. Analyzer/backend robustness audit
4. Focused production development and regression verification

The testing and robustness sessions identified missing regression coverage
for multi-file completeness behavior. Focused regression tests were added
to the existing analyzer test suite.

The final development session identified a usability gap in
`validation_recommendations`: recommendations were previously generated
only from potentially missing artifacts, so a complete change with related
artifacts could provide no validation guidance.

A focused production improvement was implemented in
`analyzer/completeness_analyzer/service.py` so recommendations are generated
from both affected-and-changed and potentially-missing artifacts.

Two new regression tests were added and one existing test was updated to
verify the behavior.

### Member 2 — Frontend and documentation workflow

Member 2 used IBM Bob for:

1. Documentation and developer-workflow investigation
2. Focused frontend usability improvement
3. Documentation correction
4. Final repository and submission-readiness verification

In the frontend development session, IBM Bob identified a small clarity
issue in the existing `ArtifactCard`: confidence values were displayed as
plain text and were not visually distinct from surrounding evidence text.

The existing UI structure was retained. A focused confidence-badge treatment
was added for `high`, `medium`, and `low` confidence values, with regression
coverage for the rendered classes.

The final verification session reviewed documentation, test/build evidence,
Bob session evidence, environment-file handling, ignored/generated files,
submission assets, and Git repository readiness against the actual
repository state.

Changes were accepted only when supported by the repository and verified
project behavior. No speculative redesign or unsupported project claims were
introduced.

### Bob session evidence

Session reports and screenshots are retained under:

```text
bob_sessions/
├── member_1/
│   ├── session_01/   Architecture orientation
│   ├── session_02/   Testing and regression
│   ├── session_03/   Robustness audit
│   └── session_04/   Focused production improvement
└── member_2/
    ├── session_01/   Documentation investigation
    ├── session_02/   Documentation correction
    ├── session_03/   Frontend usability improvement
    └── session_04/   Final repository and submission verification
```

The retained session evidence documents the tasks given to IBM Bob, findings,
implemented changes, and verification results.

## Team

**Team:** codebloom-ai

**Members:**

- **Maria Dorthy** — Backend development and analysis pipeline
- **Maria Silvia** — Frontend, documentation, presentation, video, and visual assets

---

## Project Status

Phases 1–9 have been implemented and verified.

The current project includes:

* Git change detection
* evidence-backed relationship discovery
* completeness analysis
* FastAPI API
* React dashboard
* deterministic demo scenarios
* automated tests
* reproducibility verification
* focused robustness regression coverage
* a focused developer-facing completeness recommendation improvement

Final verification includes:

* 40 backend/analyzer tests passed
* 9 frontend tests passed
* successful frontend production build
* focused robustness audit with no confirmed production defects
* focused production improvement with regression coverage
* focused frontend usability improvement with regression coverage