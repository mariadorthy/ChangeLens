# ChangeLens Architecture

Phase 2 keeps the Phase 1 separation between frontend, backend orchestration boundaries, analyzer package, and demo fixture repository.

The implemented analyzer flow is now:

```text
Git repository
      ↓
base revision + target revision
      ↓
analyzer.git_diff
      ↓
structured ChangeSet
      ↓
analyzer.impact_analyzer
      ↓
evidence-backed repository relationships
      ↓
Phase 4: completeness analysis (future)
```

The `git_diff` boundary is responsible only for factual Git change extraction: file status, paths, additions/deletions, changed hunks, and changed lines.

The `impact_analyzer` boundary consumes that factual `ChangeSet` and inspects repository artifacts for evidence-backed relationships such as imports, API consumers, tests, documentation, configuration references, and explicit symbols.

Phase 3 does not determine whether a related artifact actually needs a change. It only identifies a potential relationship and records the evidence and confidence.

The remaining completeness and report-generation modules intentionally stay as future-phase boundaries.
