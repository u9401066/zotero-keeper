"""Guard canonical docs against drifting away from the collaboration-safe workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocRule:
    path: Path
    required: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


ROOT = Path(__file__).resolve().parents[1]

RULES = (
    DocRule(
        path=ROOT / "README.zh-TW.md",
        required=(
            "import_articles",
            "check_articles_owned",
            "unified_search",
            'options="preprints"',
            'options="all_types"',
        ),
        forbidden=(
            "search_pubmed_exclude_owned",
            "quick_import_pmids",
            "import_from_pmids",
            "batch_import_from_pubmed",
            "include_preprints=true",
            "peer_reviewed_only=true",
        ),
    ),
    DocRule(
        path=ROOT / ".github" / "zotero-research-workflow.md",
        required=("import_articles", "check_articles_owned", "unified_search"),
        forbidden=(
            "search_pubmed_exclude_owned",
            "quick_import_pmids",
            "import_from_pmids",
            "batch_import_from_pubmed",
        ),
    ),
    DocRule(
        path=ROOT / ".github" / "agents" / "research.agent.md",
        required=("import_articles", "check_articles_owned", "unified_search"),
        forbidden=(
            "search_pubmed_exclude_owned",
            "quick_import_pmids",
            "import_from_pmids",
            "batch_import_from_pubmed",
        ),
    ),
    DocRule(
        path=ROOT
        / "external"
        / "pubmed-search-mcp"
        / ".github"
        / "agents"
        / "research.agent.md",
        required=("import_articles", "check_articles_owned", "unified_search"),
        forbidden=(
            "search_pubmed_exclude_owned",
            "quick_import_pmids",
            "import_from_pmids",
            "batch_import_from_pubmed",
        ),
    ),
    DocRule(
        path=ROOT
        / "vscode-extension"
        / "resources"
        / "repo-assets"
        / "pubmed-search-mcp"
        / ".github"
        / "agents"
        / "research.agent.md",
        required=("import_articles", "check_articles_owned", "unified_search"),
        forbidden=(
            "search_pubmed_exclude_owned",
            "quick_import_pmids",
            "import_from_pmids",
            "batch_import_from_pubmed",
        ),
    ),
    DocRule(
        path=ROOT / "docs" / "design" / "BATCH_IMPORT_DESIGN.md",
        required=(
            "Current Status (2026-04-09)",
            "collaboration-safe workflow",
            "import_articles",
            "check_articles_owned",
            "unified_search",
        ),
    ),
    DocRule(
        path=ROOT / "docs" / "design" / "PUBMED_MCP_OUTPUT_FORMAT_ANALYSIS.md",
        required=(
            "Current Status (2026-04-09)",
            "UnifiedArticle.to_dict()",
            'unified_search(..., output_format="json")',
        ),
    ),
    DocRule(
        path=ROOT / "docs" / "research" / "UNIFIED_SEARCH_RESEARCH.md",
        required=(
            "Current Status (2026-04-09)",
            "collaboration-safe workflow",
            "import_articles",
            "check_articles_owned",
        ),
    ),
    DocRule(
        path=ROOT / "memory-bank" / "productContext.md",
        required=(
            "collaboration-safe",
            "unified_search",
            "import_articles",
            "check_articles_owned",
        ),
        forbidden=("search_literature", "smart_add_reference"),
    ),
)


def main() -> int:
    failures: list[str] = []

    for rule in RULES:
        if not rule.path.exists():
            failures.append(f"Missing required file: {rule.path.relative_to(ROOT)}")
            continue

        text = rule.path.read_text(encoding="utf-8")

        for needle in rule.required:
            if needle not in text:
                failures.append(
                    f"{rule.path.relative_to(ROOT)} is missing required text: {needle}"
                )

        for needle in rule.forbidden:
            if needle in text:
                failures.append(
                    f"{rule.path.relative_to(ROOT)} still contains forbidden text: {needle}"
                )

    if failures:
        print("Collaboration-safe documentation guard failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Collaboration-safe documentation guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
