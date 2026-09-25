"""Deterministic repository relationship discovery for ChangeLens Phase 3."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

from analyzer.git_diff import ChangeSet


RELATIONSHIP_TYPES = {
    "import",
    "api_consumer",
    "test",
    "documentation",
    "configuration",
    "reference",
}

CONFIDENCE_LEVELS = {"high", "medium", "low"}

_IGNORED_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}

_SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
}

_DOCUMENTATION_EXTENSIONS = {
    ".md",
    ".mdx",
    ".rst",
    ".txt",
}

_CONFIGURATION_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".env",
}

_API_ROUTE_RE = re.compile(
    r"""@\w+\.(?:get|post|put|patch|delete|options|head)\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\s\S]*?\s+from\s+)?|require\s*\(\s*)["']([^"']+)["']""",
    re.MULTILINE,
)

_FETCH_RE = re.compile(
    r"""(?:fetch|axios\.(?:get|post|put|patch|delete|request))\s*\(\s*["'`]([^"'`]+)["'`]""",
    re.IGNORECASE,
)

_ENV_RE = re.compile(
    r"""(?:os\.(?:get|environ\.get)|process\.env)\s*\[?\(?\s*["']([A-Z][A-Z0-9_]*)["']""",
)

@dataclass(frozen=True)
class Relationship:
    """One evidence-backed relationship between a changed file and repository artifact."""

    path: str
    type: str
    reason: str
    confidence: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactResult:
    """Potential repository relationships discovered for one changed file."""

    changed_file: str
    relationships: tuple[Relationship, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactReport:
    """Complete Phase 3 relationship-discovery result."""

    repository: str
    changed_files: tuple[ImpactResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImpactDiscoveryError(RuntimeError):
    """Raised when repository relationship discovery cannot inspect its input."""


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _repository_files(repository: Path) -> list[Path]:
    files: list[Path] = []

    for path in repository.rglob("*"):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(repository).parts
        if any(part in _IGNORED_DIRECTORIES for part in relative_parts):
            continue

        files.append(path)

    return sorted(files, key=lambda item: _normalise_path(str(item.relative_to(repository))))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _python_module_candidates(relative_path: str) -> set[str]:
    path = Path(relative_path)
    if path.suffix != ".py":
        return set()

    without_suffix = path.with_suffix("")
    parts = list(without_suffix.parts)

    if parts and parts[-1] == "__init__":
        parts.pop()

    candidates = {".".join(parts)}

    if parts and parts[0] == "backend":
        candidates.add(".".join(parts[1:]))

    return {candidate for candidate in candidates if candidate}


def _python_imports(source: str) -> set[str]:
    imports: set[str] = set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def _javascript_imports(source: str) -> set[str]:
    return {match.group(1) for match in _JS_IMPORT_RE.finditer(source)}


def _resolve_javascript_import(
    importer: Path,
    import_specifier: str,
    repository: Path,
) -> str | None:
    if not import_specifier.startswith("."):
        return None

    candidate = (importer.parent / import_specifier).resolve()

    candidates = [
        candidate,
        candidate.with_suffix(".js"),
        candidate.with_suffix(".jsx"),
        candidate.with_suffix(".ts"),
        candidate.with_suffix(".tsx"),
        candidate / "index.js",
        candidate / "index.jsx",
        candidate / "index.ts",
        candidate / "index.tsx",
    ]

    for path in candidates:
        try:
            relative = path.relative_to(repository)
        except ValueError:
            continue

        if path.is_file():
            return _normalise_path(str(relative))

    return None

def _api_routes(source: str) -> set[str]:
    return {match.group(1) for match in _API_ROUTE_RE.finditer(source)}


def _api_consumers(source: str) -> set[str]:
    routes = set()

    for match in _FETCH_RE.finditer(source):
        value = match.group(1)
        if value.startswith("/"):
            routes.add(value)

    return routes


def _test_like(path: str) -> bool:
    name = Path(path).name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "/tests/" in f"/{_normalise_path(path)}/"
        or "/__tests__/" in f"/{_normalise_path(path)}/"
    )


def _documentation_file(path: str) -> bool:
    return Path(path).suffix.lower() in _DOCUMENTATION_EXTENSIONS


def _configuration_file(path: str) -> bool:
    return Path(path).suffix.lower() in _CONFIGURATION_EXTENSIONS


def _symbol_names(source: str) -> set[str]:
    names: set[str] = set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return names

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)

    return names


def _changed_symbols(path: Path, source: str) -> set[str]:
    if path.suffix == ".py":
        return _symbol_names(source)

    return set(
        re.findall(
            r"\b(?:function|class)\s+([A-Za-z_$][\w$]*)",
            source,
        )
    )


def _reference_evidence(
    changed_relative: str,
    changed_source: str,
    candidate_relative: str,
    candidate_source: str,
) -> Relationship | None:
    changed_path = Path(changed_relative)
    candidate_path = Path(candidate_relative)

    changed_name = changed_path.name
    changed_stem = changed_path.stem

    if candidate_relative == changed_relative:
        return None

    # 1. Direct Python import.
    if changed_path.suffix == ".py" and candidate_path.suffix == ".py":
        imported_modules = _python_imports(candidate_source)
        module_candidates = _python_module_candidates(changed_relative)

        if imported_modules & module_candidates:
            relationship_type = "test" if _test_like(candidate_relative) else "import"
            reason = (
                f"Imports Python module represented by {changed_relative}"
            )
            confidence = "high"
            return Relationship(
                path=candidate_relative,
                type=relationship_type,
                reason=reason,
                confidence=confidence,
            )

       # 2. Explicit file path reference.
    normalised_candidate_source = candidate_source.replace("\\", "/")
    path_variants = {
        changed_relative,
        f"./{changed_relative}",
        f"../{changed_relative}",
    }

    if any(value in normalised_candidate_source for value in path_variants):
        relationship_type = (
            "documentation"
            if _documentation_file(candidate_relative)
            else "configuration"
            if _configuration_file(changed_relative)
            or _configuration_file(candidate_relative)
            else "reference"
        )
        confidence = "high" if relationship_type != "documentation" else "medium"
        return Relationship(
            path=candidate_relative,
            type=relationship_type,
            reason=f"Explicitly references {changed_relative}",
            confidence=confidence,
        )

    # 3. Documentation references exact component/API names.
    if _documentation_file(candidate_relative):
        symbols = _changed_symbols(changed_path, changed_source)
        candidates = symbols | {changed_name, changed_stem}

        exact_matches = [
            value
            for value in candidates
            if value and re.search(rf"\b{re.escape(value)}\b", candidate_source)
        ]

        if exact_matches:
            return Relationship(
                path=candidate_relative,
                type="documentation",
                reason=(
                    f"Documentation explicitly references "
                    f"{', '.join(sorted(exact_matches))}"
                ),
                confidence="medium",
            )

    # 4. Configuration file references.
    if _configuration_file(changed_relative):
        config_name = changed_path.name
        config_stem = changed_path.stem

        if (
            config_name in candidate_source
            or config_stem in candidate_source
        ):
            return Relationship(
                path=candidate_relative,
                type="configuration",
                reason=f"References configuration file {changed_relative}",
                confidence="high",
            )

    # 5. Environment variable references.
    if _configuration_file(changed_relative):
        try:
            config_data = json.loads(changed_source)
        except (json.JSONDecodeError, TypeError):
            config_data = {}

        if isinstance(config_data, dict):
            keys = {
                str(key)
                for key in config_data.keys()
                if isinstance(key, str)
            }
            referenced_keys = keys & set(_ENV_RE.findall(candidate_source))
            if referenced_keys:
                return Relationship(
                    path=candidate_relative,
                    type="configuration",
                    reason=(
                        "References configuration key(s): "
                        + ", ".join(sorted(referenced_keys))
                    ),
                    confidence="medium",
                )

    return None


def _discover_for_file(
    repository: Path,
    changed_relative: str,
) -> tuple[Relationship, ...]:
    changed_path = repository / changed_relative
    changed_source = _read_text(changed_path)

    if not changed_source and not changed_path.exists():
        return ()

    changed_routes = _api_routes(changed_source)
    relationships: dict[tuple[str, str], Relationship] = {}

    for candidate in _repository_files(repository):
        candidate_relative = _normalise_path(str(candidate.relative_to(repository)))
        if candidate_relative == changed_relative:
            continue

        candidate_source = _read_text(candidate)
        if not candidate_source:
            continue

        relationship = _reference_evidence(
            changed_relative,
            changed_source,
            candidate_relative,
            candidate_source,
        )

        if relationship:
            relationships[(relationship.path, relationship.type)] = relationship
            continue

        # Resolve JavaScript/JSX/TypeScript relative imports against the
        # repository root.
        if candidate.suffix in _SOURCE_EXTENSIONS:
            for specifier in _javascript_imports(candidate_source):
                resolved = _resolve_javascript_import(
                    candidate,
                    specifier,
                    repository,
                )
                if resolved == changed_relative:
                    relationship_type = (
                        "test" if _test_like(candidate_relative) else "import"
                    )
                    relationships[(candidate_relative, relationship_type)] = Relationship(
                        path=candidate_relative,
                        type=relationship_type,
                        reason=f"Imports {changed_relative}",
                        confidence="high",
                    )
                    break

        # Detect frontend/API consumers from explicit backend route strings.
        if changed_routes:
            candidate_routes = _api_consumers(candidate_source)
            matched_routes = changed_routes & candidate_routes
            if matched_routes:
                relationships[(candidate_relative, "api_consumer")] = Relationship(
                    path=candidate_relative,
                    type="api_consumer",
                    reason=(
                        "References API route(s): "
                        + ", ".join(sorted(matched_routes))
                    ),
                    confidence="high",
                )

        # Detect source references to changed Python symbols.
        if (
            changed_path.suffix == ".py"
            and candidate.suffix == ".py"
            and not _test_like(candidate_relative)
        ):
            symbols = _changed_symbols(changed_path, changed_source)
            referenced_symbols = {
                symbol
                for symbol in symbols
                if re.search(rf"\b{re.escape(symbol)}\b", candidate_source)
            }
            if referenced_symbols:
                relationships[(candidate_relative, "reference")] = Relationship(
                    path=candidate_relative,
                    type="reference",
                    reason=(
                        "References symbol(s): "
                        + ", ".join(sorted(referenced_symbols))
                    ),
                    confidence="medium",
                )

    return tuple(
        sorted(
            relationships.values(),
            key=lambda item: (item.path, item.type),
        )
    )


def discover_relationships(
    repository_path: str,
    change_set: ChangeSet,
) -> ImpactReport:
    """Discover evidence-backed repository relationships for a ChangeSet."""
    repository = Path(repository_path).resolve()

    if not repository.is_dir():
        raise ImpactDiscoveryError(
            f"Repository path does not exist or is not a directory: {repository}"
        )

    relationships_by_file: list[ImpactResult] = []

    for changed_file in change_set.files:
        changed_relative = _normalise_path(changed_file.path)
        relationships_by_file.append(
            ImpactResult(
                changed_file=changed_relative,
                relationships=_discover_for_file(
                    repository,
                    changed_relative,
                ),
            )
        )

    return ImpactReport(
        repository=str(repository),
        changed_files=tuple(relationships_by_file),
    )


def analyze_impact(
    repository_path: str,
    change_set: ChangeSet,
) -> ImpactReport:
    """Phase 3 compatibility entry point for repository impact discovery."""
    return discover_relationships(repository_path, change_set)