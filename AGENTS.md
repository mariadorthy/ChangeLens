# ChangeLens AI Development Rules

## Product identity

- ChangeLens is a developer workflow tool.
- Core workflow: **Change → affected artifacts → actual changes → missing work → validation recommendations.**
- Do not describe ChangeLens as a generic AI code review tool.

## Engineering rules

- Prefer evidence from the repository over assumptions.
- Do not invent dependencies, relationships, or impact findings.
- Clearly distinguish detected facts from recommendations.
- Future analysis results should include a reason and confidence where applicable.
- Keep the MVP focused on helping developers understand follow-up work caused by a change.
- Do not add unnecessary infrastructure, services, frameworks, or dependencies.
- Prefer small, testable modules with explicit interfaces.
- Do not make destructive changes without approval.
- Do not claim an analyzer capability is implemented until it is actually implemented and tested.
- Keep demo-project intentionally small and useful for deterministic examples.
- Keep local development possible without paid APIs, cloud infrastructure, or external services.

## Scope discipline

- GitHub integration, CI/CD, LLM integration, autonomous code modification, complex static analysis, multi-language support, authentication, and production deployment are out of Phase 1 scope.
- Placeholder modules are acceptable in foundation phases, but they must not return fabricated analysis results.
