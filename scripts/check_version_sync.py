#!/usr/bin/env python3
"""Check release-facing Zotero Keeper and VSIX versions for drift."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SEMVER = r"\d+\.\d+\.\d+"


def _read_text(path: Path, label: str, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"{label}: required file is missing ({path})")
        return ""
    return path.read_text(encoding="utf-8")


def _extract(
    path: Path,
    label: str,
    pattern: str,
    errors: list[str],
    *,
    flags: int = 0,
) -> str:
    content = _read_text(path, label, errors)
    if not content:
        return ""
    match = re.search(pattern, content, flags)
    if not match:
        errors.append(f"{label}: cannot find a release version")
        return ""
    return match.group("version")


def _compare(label: str, actual: str, expected: str, errors: list[str]) -> None:
    if actual and actual != expected:
        errors.append(f"VERSION MISMATCH: {label}={actual} != expected={expected}")


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    content = _read_text(path, label, errors)
    if not content:
        return {}
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON ({exc})")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label}: expected a JSON object")
        return {}
    return value


def _load_toml(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    content = _read_text(path, label, errors)
    if not content:
        return {}
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{label}: invalid TOML ({exc})")
        return {}


def validate_release_tag(
    environment: Mapping[str, str],
    extension_version: str,
    keeper_version: str,
    errors: list[str],
) -> None:
    """Validate a GitHub tag against the product version it publishes."""
    if environment.get("GITHUB_REF_TYPE") != "tag":
        return

    ref_name = environment.get("GITHUB_REF_NAME", "")
    if not ref_name:
        ref = environment.get("GITHUB_REF", "")
        prefix = "refs/tags/"
        if ref.startswith(prefix):
            ref_name = ref[len(prefix) :]

    if not ref_name:
        errors.append("GitHub tag validation: GITHUB_REF_TYPE=tag but no tag name was provided")
        return

    expected_extension_tag = f"v{extension_version}-ext"
    expected_keeper_tag = f"v{keeper_version}"
    if ref_name not in {expected_extension_tag, expected_keeper_tag}:
        errors.append(f"TAG MISMATCH: {ref_name} is neither extension tag {expected_extension_tag} nor Keeper tag {expected_keeper_tag}")


def collect_version_errors(
    repo_root: Path,
    environment: Mapping[str, str] | None = None,
) -> tuple[list[str], str, str]:
    """Return version drift errors plus the canonical VSIX and Keeper versions."""
    errors: list[str] = []
    extension_root = repo_root / "vscode-extension"
    keeper_root = repo_root / "mcp-server"

    extension_package = _load_json(extension_root / "package.json", "vscode-extension/package.json", errors)
    extension_version = str(extension_package.get("version", ""))
    if not re.fullmatch(SEMVER, extension_version):
        errors.append("vscode-extension/package.json: version must use X.Y.Z semantic versioning")
    expected_extension_tag = f"v{extension_version}-ext"

    keeper_pyproject = _load_toml(keeper_root / "pyproject.toml", "mcp-server/pyproject.toml", errors)
    keeper_version = str(keeper_pyproject.get("project", {}).get("version", ""))
    if not re.fullmatch(SEMVER, keeper_version):
        errors.append("mcp-server/pyproject.toml: project.version must use X.Y.Z semantic versioning")

    # Extension release surface.
    extension_versions = [
        (
            "vscode-extension/src/statusBar.ts private version",
            _extract(
                extension_root / "src" / "statusBar.ts",
                "vscode-extension/src/statusBar.ts private version",
                rf"private\s+version:\s*string\s*=\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "vscode-extension/src/statusBar.ts package fallback",
            _extract(
                extension_root / "src" / "statusBar.ts",
                "vscode-extension/src/statusBar.ts package fallback",
                rf"packageJson\.version\s*\|\|\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "vscode-extension/CHANGELOG.md first entry",
            _extract(
                extension_root / "CHANGELOG.md",
                "vscode-extension/CHANGELOG.md first entry",
                rf"^## \[(?P<version>{SEMVER})\]",
                errors,
                flags=re.MULTILINE,
            ),
        ),
    ]
    for label, actual in extension_versions:
        _compare(label, actual, extension_version, errors)

    extension_lock = _load_json(
        extension_root / "package-lock.json",
        "vscode-extension/package-lock.json",
        errors,
    )
    lock_versions = [
        ("vscode-extension/package-lock.json root", extension_lock.get("version", "")),
        (
            "vscode-extension/package-lock.json packages['']",
            extension_lock.get("packages", {}).get("", {}).get("version", ""),
        ),
    ]
    for label, actual in lock_versions:
        if not actual:
            errors.append(f"{label}: version is missing")
        _compare(label, str(actual), extension_version, errors)

    extension_readme = _read_text(extension_root / "README.md", "vscode-extension/README.md", errors)
    if extension_readme and f"What's New in v{extension_version}" not in extension_readme:
        errors.append(f"vscode-extension/README.md: missing current What's New heading for v{extension_version}")

    walkthrough = _read_text(
        extension_root / "resources" / "walkthrough" / "packages.md",
        "vscode-extension/resources/walkthrough/packages.md",
        errors,
    )
    if walkthrough and expected_extension_tag not in walkthrough:
        errors.append(f"vscode-extension/resources/walkthrough/packages.md: missing extension package tag {expected_extension_tag}")

    keeper_package_ts = extension_root / "src" / "zoteroKeeperPackage.ts"
    runtime_extension_tag = _extract(
        keeper_package_ts,
        "vscode-extension/src/zoteroKeeperPackage.ts archive tag",
        rf"/tags/(?P<version>v{SEMVER}-ext)\.tar\.gz",
        errors,
    )
    if runtime_extension_tag and runtime_extension_tag != expected_extension_tag:
        errors.append(
            f"TAG MISMATCH: vscode-extension/src/zoteroKeeperPackage.ts={runtime_extension_tag} != expected={expected_extension_tag}"
        )

    mac_test_extension_tag = _extract(
        extension_root / "tests" / "test_mac_compatibility.py",
        "vscode-extension/tests/test_mac_compatibility.py archive assertion",
        rf"assertIn\(['\"](?P<version>v{SEMVER}-ext)\.tar\.gz",
        errors,
    )
    if mac_test_extension_tag and mac_test_extension_tag != expected_extension_tag:
        errors.append(
            f"TAG MISMATCH: vscode-extension/tests/test_mac_compatibility.py={mac_test_extension_tag} != expected={expected_extension_tag}"
        )

    # Keeper package/runtime/install pins and hard-coded release assertions.
    keeper_versions = [
        (
            "mcp-server/src/zotero_mcp/__init__.py",
            _extract(
                keeper_root / "src" / "zotero_mcp" / "__init__.py",
                "mcp-server/src/zotero_mcp/__init__.py",
                rf"^__version__\s*=\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
                flags=re.MULTILINE,
            ),
        ),
        (
            "mcp-server/src/zotero_mcp/infrastructure/mcp/config.py",
            _extract(
                keeper_root / "src" / "zotero_mcp" / "infrastructure" / "mcp" / "config.py",
                "mcp-server/src/zotero_mcp/infrastructure/mcp/config.py",
                rf"^\s*version:\s*str\s*=\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
                flags=re.MULTILINE,
            ),
        ),
        (
            "vscode-extension/src/zoteroKeeperPackage.ts ZOTERO_KEEPER_VERSION",
            _extract(
                keeper_package_ts,
                "vscode-extension/src/zoteroKeeperPackage.ts ZOTERO_KEEPER_VERSION",
                rf"ZOTERO_KEEPER_VERSION\s*=\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "CHANGELOG.md first entry",
            _extract(
                repo_root / "CHANGELOG.md",
                "CHANGELOG.md first entry",
                rf"^## \[(?P<version>{SEMVER})\]",
                errors,
                flags=re.MULTILINE,
            ),
        ),
        (
            "mcp-server/tests/unit/infrastructure/test_config.py",
            _extract(
                keeper_root / "tests" / "unit" / "infrastructure" / "test_config.py",
                "mcp-server/tests/unit/infrastructure/test_config.py",
                rf"config\.version\s*==\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "vscode-extension/src/test/pythonEnvironment.test.ts",
            _extract(
                extension_root / "src" / "test" / "pythonEnvironment.test.ts",
                "vscode-extension/src/test/pythonEnvironment.test.ts",
                rf"strictEqual\(ZOTERO_KEEPER_VERSION,\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "vscode-extension/src/test/mcpProvider.test.ts",
            _extract(
                extension_root / "src" / "test" / "mcpProvider.test.ts",
                "vscode-extension/src/test/mcpProvider.test.ts",
                rf"strictEqual\(servers\[0\]\.version,\s*['\"](?P<version>{SEMVER})['\"]",
                errors,
            ),
        ),
        (
            "vscode-extension/tests/test_python_env_edge_cases.py",
            _extract(
                extension_root / "tests" / "test_python_env_edge_cases.py",
                "vscode-extension/tests/test_python_env_edge_cases.py",
                rf"\(['\"]zotero-keeper['\"],\s*['\"]zotero_mcp['\"],\s*['\"](?P<version>{SEMVER})['\"]\)",
                errors,
            ),
        ),
    ]
    for label, actual in keeper_versions:
        _compare(label, actual, keeper_version, errors)

    keeper_lock = _load_toml(keeper_root / "uv.lock", "mcp-server/uv.lock", errors)
    keeper_lock_packages = [
        package for package in keeper_lock.get("package", []) if isinstance(package, dict) and package.get("name") == "zotero-keeper"
    ]
    if len(keeper_lock_packages) != 1:
        errors.append("mcp-server/uv.lock: expected exactly one zotero-keeper project package")
    else:
        lock_keeper_version = str(keeper_lock_packages[0].get("version", ""))
        if not lock_keeper_version:
            errors.append("mcp-server/uv.lock zotero-keeper: version is missing")
        _compare(
            "mcp-server/uv.lock zotero-keeper",
            lock_keeper_version,
            keeper_version,
            errors,
        )

    validate_release_tag(
        os.environ if environment is None else environment,
        extension_version,
        keeper_version,
        errors,
    )
    return errors, extension_version, keeper_version


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    errors, extension_version, keeper_version = collect_version_errors(repo_root)

    if errors:
        print("Version sync check FAILED:")
        for error in errors:
            print(f"  - {error}")
        print(f"\nExpected versions: VSIX {extension_version or '<missing>'}; Zotero Keeper {keeper_version or '<missing>'}")
        print("Fix: update package metadata, runtime pins, locks, changelogs, tests, walkthroughs, and release tags together.")
        return 1

    print(f"Version sync OK: VSIX {extension_version}; Zotero Keeper {keeper_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
