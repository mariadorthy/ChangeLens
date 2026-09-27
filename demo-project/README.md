
# ChangeLens Demo Project

The `demo-project` directory is a deliberately small task-management application used as a deterministic fixture for ChangeLens analysis.

It is not intended to be a production application.

---

## Purpose

The fixture contains several types of relationships that ChangeLens can discover:

```text
Backend API
    ↓
Frontend API client
    ↓
Frontend UI

Backend service
    ↓
Tests

Configuration
    ↓
Backend behavior

API behavior
    ↓
Documentation
````

These relationships make it possible to demonstrate both complete and potentially incomplete changes.

---

## Structure

```text
demo-project/
├── backend/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── main.py
├── config/
├── docs/
├── frontend/
├── tests/
└── README.md
```

---

## Demo Scenarios

The fixture is used by the verified ChangeLens scenarios documented in the root project README.

The scenarios demonstrate:

* a complete change with no potentially missing artifacts
* a source change with a related source reference
* an API change with both documentation and source relationships

The scenarios use real Git revisions from the project history.

---

## Design Principle

The demo project is intentionally small.

Its purpose is to make repository relationships easy to understand and provide deterministic examples for testing and demonstration.

It should not be treated as a representative production codebase or as a benchmark for general dependency analysis.
