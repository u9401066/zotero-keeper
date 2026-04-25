#!/usr/bin/env python3
"""
Pre-commit hook: Check version sync across vscode-extension files.

Ensures release-facing version references stay in sync:
1. vscode-extension/package.json  "version": "X.Y.Z"
2. vscode-extension/src/statusBar.ts  private version: string = 'X.Y.Z'
3. vscode-extension/CHANGELOG.md  ## [X.Y.Z] - YYYY-MM-DD  (first entry)
4. vscode-extension/package-lock.json package versions
5. vscode-extension/README.md "What's New in vX.Y.Z"
6. walkthrough/installer references to vX.Y.Z-ext
7. zoteroKeeperPackage.ts package source archive reference to vX.Y.Z-ext
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
    expected_ext_tag = f"v{pkg_version}-ext"

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

    # 4. package-lock.json
    package_lock = root / "package-lock.json"
    if package_lock.exists():
        lock = json.loads(package_lock.read_text(encoding="utf-8"))
        lock_versions = [
            ("package-lock.json root", lock.get("version", "")),
            (
                "package-lock.json packages['']",
                lock.get("packages", {}).get("", {}).get("version", ""),
            ),
        ]
        for label, value in lock_versions:
            if value and value != pkg_version:
                errors.append(
                    f"VERSION MISMATCH: package.json={pkg_version} != {label}={value}"
                )

    # 5. README current-version heading
    readme = root / "README.md"
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
        if f"What's New in v{pkg_version}" not in content:
            errors.append(
                f"README.md: missing current What's New heading for v{pkg_version}"
            )

    # 6. Walkthrough/installer package references
    packages_md = root / "resources" / "walkthrough" / "packages.md"
    if packages_md.exists():
        content = packages_md.read_text(encoding="utf-8")
        if expected_ext_tag not in content:
            errors.append(
                f"packages.md: missing extension package tag {expected_ext_tag}"
            )

    # 7. Runtime installer package reference
    zotero_pkg = root / "src" / "zoteroKeeperPackage.ts"
    if zotero_pkg.exists():
        content = zotero_pkg.read_text(encoding="utf-8")
        if expected_ext_tag not in content:
            errors.append(
                f"zoteroKeeperPackage.ts: missing extension package tag {expected_ext_tag}"
            )

    if errors:
        print("Version sync check FAILED:")
        for e in errors:
            print(f"  - {e}")
        print(f"\nExpected version: {pkg_version} (from package.json)")
        print(
            "Fix: update package metadata, docs, walkthroughs, and installer package refs together."
        )
        return 1

    print(f"Version sync OK: {pkg_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
