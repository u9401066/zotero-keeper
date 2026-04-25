#!/usr/bin/env python3
"""Validate that project assistant harness skills are discoverable.

Checks skill directories under:
- .codex/skills/
- .cline/skills/
- .clinerules/skills/
- .claude/skills/

Each skill directory must contain a SKILL.md with YAML frontmatter including:
- name (must match the directory name exactly)
- description
"""

from __future__ import annotations

from pathlib import Path

import yaml

SKILL_ROOTS = (
    Path(".codex/skills"),
    Path(".cline/skills"),
    Path(".clinerules/skills"),
    Path(".claude/skills"),
    Path("vscode-extension/resources/repo-assets/keeper/.codex/skills"),
    Path("vscode-extension/resources/repo-assets/keeper/.cline/skills"),
    Path("vscode-extension/resources/repo-assets/pubmed-search-mcp/.codex/skills"),
    Path("vscode-extension/resources/repo-assets/pubmed-search-mcp/.cline/skills"),
    Path("vscode-extension/resources/repo-assets/pubmed-search-mcp/.claude/skills"),
)

REQUIRED_SKILL_DIRS = (
    Path(".codex/skills/zotero-keeper-harness"),
    Path(".codex/skills/pubmed-search-mcp-harness"),
    Path(".cline/skills/zotero-keeper-harness"),
    Path(".cline/skills/pubmed-search-mcp-harness"),
    Path(
        "vscode-extension/resources/repo-assets/keeper/.codex/skills/zotero-keeper-harness"
    ),
    Path(
        "vscode-extension/resources/repo-assets/keeper/.cline/skills/zotero-keeper-harness"
    ),
    Path(
        "vscode-extension/resources/repo-assets/pubmed-search-mcp/.codex/skills/pubmed-search-mcp-harness"
    ),
    Path(
        "vscode-extension/resources/repo-assets/pubmed-search-mcp/.cline/skills/pubmed-search-mcp-harness"
    ),
)


def parse_frontmatter(text: str, *, path: Path) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing YAML frontmatter opening '---'")

    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        raise ValueError(f"{path}: unterminated YAML frontmatter")

    frontmatter = "\n".join(lines[1:end]).strip() + "\n"
    try:
        meta = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML frontmatter: {exc}") from exc

    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: YAML frontmatter must be a mapping/dict")

    normalized: dict[str, str] = {}
    for key, value in meta.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            normalized[key] = value
        elif value is None:
            normalized[key] = ""
        else:
            normalized[key] = str(value)

    return normalized


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]

    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{skill_md}: not valid UTF-8"]

    try:
        meta = parse_frontmatter(text, path=skill_md)
    except ValueError as exc:
        return [str(exc)]

    name = meta.get("name", "").strip()
    description = meta.get("description", "").strip()
    if not name:
        errors.append(f"{skill_md}: missing required frontmatter field 'name'")
    if not description:
        errors.append(f"{skill_md}: missing required frontmatter field 'description'")
    if description and len(description) > 1024:
        errors.append(f"{skill_md}: description exceeds 1024 characters")

    if name and name != skill_dir.name:
        errors.append(
            f"{skill_md}: frontmatter name '{name}' does not match directory '{skill_dir.name}'"
        )

    return errors


def iter_skill_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def main() -> int:
    errors: list[str] = []
    checked = 0

    for required_dir in REQUIRED_SKILL_DIRS:
        if not required_dir.is_dir():
            errors.append(
                f"{required_dir}: required assistant harness skill directory is missing"
            )

    for root in SKILL_ROOTS:
        for skill_dir in iter_skill_dirs(root):
            checked += 1
            errors.extend(validate_skill_dir(skill_dir))

    if checked == 0:
        print(
            "No project skills found under .codex/skills/, .cline/skills/, .clinerules/skills/, or .claude/skills/"
        )
        return 1

    if errors:
        print("Cline skill audit FAILED:\n")
        for err in errors:
            print(f"- {err}")
        return 2

    print(f"Cline skill audit OK ({checked} skills checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
