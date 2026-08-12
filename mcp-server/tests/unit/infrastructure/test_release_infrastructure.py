"""Release workflow and managed-install smoke contract tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def _load_managed_smoke():
    path = REPO_ROOT / "vscode-extension" / "tests" / "test_uv_managed_install_smoke.py"
    spec = importlib.util.spec_from_file_location("test_uv_managed_install_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_managed_smoke_accepts_release_archive_source_override(monkeypatch) -> None:
    managed_smoke = _load_managed_smoke()
    archive = "https://example.invalid/archive/refs/tags/v1.2.3-ext.tar.gz"
    monkeypatch.setenv("ZOTERO_KEEPER_PACKAGE_SOURCE", archive)

    requirement, description = managed_smoke.resolve_zotero_keeper_package()

    assert requirement == f"zotero-keeper @ {archive}#subdirectory=mcp-server"
    assert description == f"environment source: {archive}"


def test_managed_smoke_preserves_complete_pep_508_override(monkeypatch) -> None:
    managed_smoke = _load_managed_smoke()
    requirement = "zotero-keeper @ https://example.invalid/pkg.tar.gz#subdirectory=mcp-server"
    monkeypatch.setenv("ZOTERO_KEEPER_PACKAGE_SOURCE", requirement)

    resolved, _ = managed_smoke.resolve_zotero_keeper_package()

    assert resolved == requirement


def test_publish_workflow_reuses_the_checked_vsix() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish-extension.yml").read_text(encoding="utf-8")

    assert 'npm run package -- --out "$filename"' in workflow
    assert '-VsixPath "${{ steps.package.outputs.filename }}"' in workflow
    assert 'vsce publish --packagePath "${{ steps.package.outputs.filename }}"' in workflow
    assert "files: ${{ steps.package.outputs.repository_path }}" in workflow
    assert "npm run publish" not in workflow


def test_publish_workflow_runs_keeper_and_local_api_wire_tests_before_packaging() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish-extension.yml").read_text(encoding="utf-8")

    test_step = workflow.index("Test Keeper and Zotero 10 Local API wire contract")
    package_step = workflow.index("Package extension")
    assert test_step < package_step
    assert "uv sync --frozen --group dev" in workflow[test_step:package_step]
    assert "uv run pytest tests/" in workflow[test_step:package_step]


def test_tag_publish_smoke_installs_the_tag_archive() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish-extension.yml").read_text(encoding="utf-8")

    assert "ZOTERO_KEEPER_PACKAGE_SOURCE:" in workflow
    assert "/archive/refs/tags/${{ github.ref_name }}.tar.gz" in workflow
