# ChangeLens — Submission Assets

This document is our index for the final ChangeLens submission assets.

The `README.md` explains the product and how to reproduce it. `docs/architecture.md` explains the technical architecture. The presentation deck is retained in `docs/assets/`, while the demo video is submitted separately through the hackathon platform. Each asset has a clear purpose.

---

## Project Identity

**Project Title:** ChangeLens

**Tagline:** Know what else needs to change.

**Category:** Developer Tools / Static Analysis

---

## Submission Assets

The final submission consists of the following artifacts:

| Asset                  | Purpose                                                               | Status                      |
| ---------------------- | --------------------------------------------------------------------- | --------------------------- |
| `README.md`            | Product explanation, workflow, reproduction, testing, and limitations | Ready                       |
| `docs/architecture.md` | Technical architecture and data flow                                  | Ready                       |
| Presentation deck | Judge-facing product story and engineering evidence | Ready |
| Demo video             | Three-minute product demonstration                                    | Prepared separately         |
| Cover image            | Submission branding / thumbnail                                       | Ready        |
| Product screenshots    | Visual evidence of the working dashboard                              | Ready                       |
| IBM Bob evidence       | Verified Bob contribution and session evidence                         | Ready                       |

---

## Presentation Deck

The presentation is a separate submission artifact.

It should cover:

1. ChangeLens and tagline
2. Developer problem
3. Why a Git diff alone is not enough
4. ChangeLens solution
5. Architecture / workflow
6. Evidence-backed relationships
7. Complete scenario
8. Potentially incomplete / hidden dependency scenario
9. IBM Bob evidence
10. Engineering and testing evidence
11. Value and future direction
12. Final takeaway

The actual slide content should remain in the presentation file rather than being duplicated in this repository document.

---

## Demo Video

The demo video is a separate submission artifact.

Target duration:

**Approximately 3 minutes**

The recording should demonstrate:

1. The developer problem
2. The ChangeLens workflow
3. Scenario 1 — Complete
4. Scenario 2 — Potentially Incomplete
5. Scenario 3 — Hidden Collateral Dependency
6. Engineering verification
7. Final ChangeLens takeaway

The actual narration and screen recording should remain in the video rather than being duplicated in this document.

**Demo Video:** [Watch the ChangeLens Demo](https://canva.link/1f4i04vwug4stfc)

---

## Required Product Screenshots

Capture the following from the working application:

* [x] Dashboard initial state
* [x] Scenario 1 — Complete
* [x] Scenario 2 — Potentially Incomplete
* [x] Scenario 3 — Hidden Collateral Dependency
* [x] Error state

Screenshots should show the actual working application and should not contain fabricated results.

---

## Engineering Evidence

Capture or retain evidence for:

* [x] Python test result
* [x] Frontend test result
* [x] Frontend production build
* [x] Three verified Git scenarios

Current verified results:

```text
python -m pytest -q
40 passed, 1 pre-existing deprecation warning

npm test
9 tests passed

npm run build
successful
```

The existing Starlette/httpx deprecation warning is pre-existing and should not be presented as a test failure. The final backend/analyzer verification completed with 40 passing tests.

---

## Cover Image

Required text:

**ChangeLens**

**Know what else needs to change.**

Suggested visual:

```text
Code Change
     ↓
Related Artifacts
     ↓
Completeness Check
     ↓
Actionable Checklist
```

The design should be:

* technical
* clean
* readable at thumbnail size
* consistent with the dashboard
* free of unsupported AI/LLM claims
* free of fabricated metrics

---

## Submission Description

### Short Description

ChangeLens is a developer workflow tool that analyzes a Git change and identifies related repository artifacts that may also need attention.

### Long Description

We built ChangeLens to help developers answer a practical question after making a code change: what else may need attention?

A Git diff shows which files changed between two revisions, but related source files, tests, documentation, configuration, and API consumers may also be affected. ChangeLens extends the normal change-review workflow by discovering evidence-backed relationships between changed files and other repository artifacts.

Our pipeline compares two Git revisions, builds a structured change set, discovers deterministic relationships, and evaluates whether related artifacts were also included in the change. The result separates changed files, affected-and-changed artifacts, and potentially missing artifacts.

Each finding can include relationship type, evidence, and confidence so that developers can review why an artifact was surfaced. A potentially missing artifact is not treated as a guaranteed required change.

We expose the analysis through a FastAPI backend and present the results through a React and Vite dashboard. We verified the implementation with automated backend/analyzer tests, frontend tests, a production build, and three deterministic Git scenarios covering complete and potentially incomplete changes.

ChangeLens is intentionally a local, deterministic MVP. It does not currently provide remote GitHub analysis, LLM-based analysis, or autonomous code modification.

It should accurately describe:

* the developer problem
* the ChangeLens workflow
* relationship discovery
* completeness analysis
* evidence and confidence
* the React dashboard
* the FastAPI backend
* deterministic verification

No unsupported capabilities or fabricated metrics should be added.

---

## Technology / Category Tags

Use only technologies actually present in the repository:

* Python
* FastAPI
* Uvicorn
* React
* Vite
* Vitest
* Git
* Static Analysis
* Developer Tools

---

## IBM Bob Evidence

IBM Bob 2.0 was used as a genuine development and verification assistant
throughout the ChangeLens workflow.

Our use of IBM Bob covered:

* repository and architecture review
* testing and regression analysis
* robustness review
* focused production development
* frontend usability improvement
* documentation review and correction
* final repository and submission-readiness verification

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
`validation_recommendations`: recommendations were generated only from
potentially missing artifacts, so a complete change with related artifacts
could provide no validation guidance.

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

The frontend development session identified a clarity issue in the existing
`ArtifactCard`: confidence values were displayed as plain text and were not
visually distinct from surrounding evidence text.

The existing UI structure was retained. A focused confidence-badge treatment
was added for `high`, `medium`, and `low` confidence values, with regression
coverage for the rendered classes.

The final verification session reviewed documentation, test/build evidence,
Bob session evidence, environment-file handling, ignored/generated files,
submission assets, and Git repository readiness against the actual
repository state.

### Evidence

IBM Bob session reports and evidence are retained under:

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
Each retained session report records the task, IBM Bob interaction, actual
changes or findings, and verification results.

No unsupported IBM Bob contribution or project capability is claimed.

## Final Submission Checklist

### Documentation

* [x] README completed
* [x] Architecture documentation completed
* [x] Submission asset index completed
* [x] Demo scenarios documented
* [x] Reproduction instructions documented
* [x] Testing documented
* [x] Known limitations documented

### Presentation

* [x] Final PPT created
* [x] 10–12 slides
* [x] Demo scenarios match verified results
* [x] Testing evidence is accurate
* [x] No unsupported claims
* [x] IBM Bob section updated only with verified evidence

### Video

* [x] Final video recorded
* [x] Approximately 3 minutes
* [x] Shows actual ChangeLens dashboard
* [x] Shows the three verified scenarios
* [x] No fabricated results
* [x] Final takeaway included

### Visual Assets

* [x] Cover image created
* [x] Dashboard screenshot captured
* [x] Scenario 1 screenshot captured
* [x] Scenario 2 screenshot captured
* [x] Scenario 3 screenshot captured
* [x] Error-state screenshot captured

### Repository

* [x] `.gitignore` verified — `venv/`, `node_modules/`, `dist/`, `__pycache__/`, `.env` all ignored
* [x] `.env.example` verified — contains no secrets or real values
* [x] No secrets committed — confirmed
* [x] Generated artifacts ignored — confirmed
* [x] Documentation contains no outdated phase claims 
* [x] Final tests rerun
* [x] Final build rerun

---

## Submission Principle

The repository documentation should explain the project and make it reproducible.

The presentation should tell the story.

The video should demonstrate the product.

The screenshots should provide visual evidence.

These assets should complement one another rather than duplicate one another.
