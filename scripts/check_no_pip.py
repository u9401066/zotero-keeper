#!/usr/bin/env python3
"""Pre-commit hook: Ban pip usage (enforce uv only).

Scans staged files for 'pip install' or 'python -m pip' usage.
Ignores comments, documentation about pip (uv-enforcer, bylaws),
and 'uv pip install' commands.
"""

import re
import sys

# Files that legitimately discuss pip (documentation, skills, etc.)
EXCLUDED_PATTERNS = [
    r"\.pre-commit-config\.yaml$",
    r"node_modules",
    r"\.git[/\\]",
    r"CHANGELOG\.md$",
    r"uv-enforcer[/\\]",  # uv-enforcer skill explains pip→uv
    r"python-environment\.md$",  # bylaws explaining pip ban
    r"REFERENCE_REPOSITORIES\.md$",  # third-party docs
    r"\.ris$",  # bibliography files
    r"check_no_pip\.py$",  # this script itself
    r"precommit_.*\.txt$",  # pre-commit log files
]


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    matches: list[tuple[str, int, str]] = []

    for filepath in sys.argv[1:]:
        # Skip excluded files
        if any(re.search(pat, filepath) for pat in EXCLUDED_PATTERNS):
            continue

        try:
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

        for i, line in enumerate(content.splitlines()):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            # Skip lines that are clearly uv pip (e.g., uvPath}" pip, uv pip, uv run pip)
            if re.search(
                r'uv["\'\'\s}\)]+pip\s+install|uv\s+pip\s+install|uv\s+pip\s+uninstall|uv\s+run\s+pip|uvPath[}"\'\'\s]+\s*pip\s+install',
                line,
            ):
                continue
            # Match standalone pip install / python -m pip
            if re.search(r"\bpip\s+install\b|python\s+-m\s+pip\b", line):
                matches.append((filepath, i + 1, stripped))

    if matches:
        print("ERROR: pip usage detected (use uv instead):")
        for filepath, lineno, line in matches:
            print(f"  {filepath}:{lineno}: {line}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
