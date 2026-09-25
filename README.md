# ChangeLens

> **Know what else needs to change.**

ChangeLens is a developer workflow tool designed to answer:

> “I changed this code — what else do I need to update?”

The project is being built incrementally. Phase 1 established the runnable foundation. Phase 2 adds deterministic Git change detection. Later phases will use those facts to discover potentially affected artifacts and identify potentially missing follow-up work.

## Current status

### Phase 1 — Project foundation

Complete. The project contains the frontend, FastAPI backend, analyzer boundaries, demo repository, tests, and documentation.

### Phase 2 — Change Detection Engine

Complete. `analyzer.git_diff` compares two explicit Git revisions and returns a structured change set containing changed files, statuses, additions/deletions, hunks, and changed lines.

It does **not** yet discover affected files, analyze dependencies, determine completeness, or generate missing-work recommendations.

## Planned workflow

```text
Code change
    ↓
Git change detection                  ← implemented
    ↓
Discover affected artifacts           ← future
    ↓
Compare against actual changes       ← future
    ↓
Identify potentially missing work    ← future
    ↓
Produce evidence-backed report       ← future
    ↓
Validation recommendations            ← future
```

## Architecture

```text
┌──────────────┐       HTTP       ┌──────────────┐
│   Frontend   │ ───────────────> │    Backend   │
│ React + Vite │                  │   FastAPI    │
└──────────────┘                  └──────┬───────┘
                                        │
                           future analysis boundaries
                                        │
                       ┌────────────────┴───────────────┐
                       │ Analyzer package               │
                       │ git_diff / parser / dependency│
                       │ impact / completeness / report│
                       └────────────────────────────────┘

                 demo-project = small task-management fixture repository
```

## Project structure

```text
changelens/
├── frontend/              # React + Vite UI
├── backend/               # FastAPI application and boundaries
├── analyzer/              # Repository/change analysis package
├── demo-project/          # Small task-management fixture repository
├── tests/                 # Cross-project/integration test area
├── docs/                  # Project documentation
├── bob_sessions/          # Reserved for development session artifacts
├── .env.example           # Local environment template
├── AGENTS.md              # AI-assisted development rules
├── LICENSE
└── README.md
```

## Phase 2 change detection

The change detector accepts:

- a Git repository path
- a base revision, such as `HEAD~1`
- a target revision, such as `HEAD`

Example:

```python
from analyzer.git_diff import extract_changed_files

changes = extract_changed_files("/path/to/repository", "HEAD~1", "HEAD")
print(changes.to_dict())
```

A result contains the resolved revision IDs and file records such as:

```json
{
  "path": "backend/api/tasks.py",
  "status": "modified",
  "old_path": null,
  "additions": 8,
  "deletions": 3,
  "hunks": [
    {
      "old_start": 10,
      "old_count": 5,
      "new_start": 10,
      "new_count": 10
    }
  ]
}
```

Supported statuses are `added`, `modified`, `deleted`, and Git-detected `renamed`. Invalid repositories and revisions raise clear `ChangeDetectionError` exceptions.

## Local setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Git

No cloud service or paid API is required.

### Backend

From `backend/`:

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The health endpoint is:

```text
GET http://127.0.0.1:8000/health
```

### Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Vite will print the local development URL.

### Tests

Backend tests:

```bash
cd backend
pytest -q
```

Analyzer tests:

```bash
cd analyzer
pytest -q
```

Frontend tests:

```bash
cd frontend
npm test
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Environment

`.env.example` is included for future configuration. No environment variables or secrets are required for the Phase 2 change detector.

## Future work

Later phases may add repository parsing, dependency/impact discovery, completeness checks, report generation, and optional integrations. Those capabilities are deliberately not represented as complete here.
