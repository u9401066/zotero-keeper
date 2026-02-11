#!/usr/bin/env python3
"""
Pre-commit hook: Check version sync across vscode-extension files.

Ensures these three locations have the same version:
1. vscode-extension/package.json  "version": "X.Y.Z"
2. vscode-extension/src/statusBar.ts  private version: string = 'X.Y.Z'
3. vscode-extension/CHANGELOG.md  ## [X.Y.Z] - YYYY-MM-DD  (first entry)
"""

import json
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "vscode-extension"
    errors: list[str] = []

    # 1. package.json
    pkg_json = root / "package.json"
    if not pkg_json.exists():
        print("SKIP: vscode-extension/package.json not found")
        return 0

    with open(pkg_json, encoding="utf-8") as f:
        pkg_version = json.load(f).get("version", "")

    # 2. statusBar.ts
    status_bar = root / "src" / "statusBar.ts"
    sb_version = ""
    if status_bar.exists():
        content = status_bar.read_text(encoding="utf-8")
        m = re.search(r"private\s+version:\s*string\s*=\s*['\"]([^'\"]+)['\"]", content)
        if m:
            sb_version = m.group(1)
        else:
            errors.append("statusBar.ts: cannot find 'private version' field")

    # 3. CHANGELOG.md (first ## [X.Y.Z] entry)
    changelog = root / "CHANGELOG.md"
    cl_version = ""
    if changelog.exists():
        content = changelog.read_text(encoding="utf-8")
        m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", content, re.MULTILINE)
        if m:
            cl_version = m.group(1)
        else:
            errors.append("CHANGELOG.md: cannot find ## [X.Y.Z] entry")

    # Compare
    if pkg_version and sb_version and pkg_version != sb_version:
        errors.append(
            f"VERSION MISMATCH: package.json={pkg_version} != statusBar.ts={sb_version}"
        )

    if pkg_version and cl_version and pkg_version != cl_version:
        errors.append(
            f"VERSION MISMATCH: package.json={pkg_version} != CHANGELOG.md={cl_version}"
        )

    if errors:
        print("Version sync check FAILED:")
        for e in errors:
            print(f"  - {e}")
        print(f"\nExpected version: {pkg_version} (from package.json)")
        print("Fix: update all three files to the same version before committing.")
        return 1

    print(f"Version sync OK: {pkg_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
