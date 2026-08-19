#!/usr/bin/env python3
"""Smoke-test the installer contract with a real uv-managed Python venv.

This intentionally exercises the failure mode that prompted the fix:
installing packages, including numpy, must write into a temporary venv instead
of the system interpreter's site-packages.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tomllib


PYTHON_VERSION = "3.12"
REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER = REPO_ROOT / "mcp-server"
KEEPER_VERSION = str(tomllib.loads((MCP_SERVER / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PUBMED_SEARCH_FIXED_COMMIT = "febf53a8ff1ee253a625869ba251365f73a23c68"  # pragma: allowlist secret
PUBMED_SEARCH_PACKAGE = f"pubmed-search-mcp @ https://github.com/u9401066/pubmed-search-mcp/archive/{PUBMED_SEARCH_FIXED_COMMIT}.tar.gz"


def resolve_zotero_keeper_package() -> tuple[str, str]:
    """Resolve local source by default, with an explicit release-archive override."""
    override = os.environ.get("ZOTERO_KEEPER_PACKAGE_SOURCE", "").strip()
    if not override:
        return str(MCP_SERVER), f"local path: {MCP_SERVER}"

    if override.startswith("zotero-keeper @ "):
        return override, f"environment requirement: {override}"

    source = override
    if "://" in source and "#subdirectory=" not in source:
        source = f"{source}#subdirectory=mcp-server"
    return f"zotero-keeper @ {source}", f"environment source: {override}"


def run(cmd: list[str], timeout: int = 600, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = {
        **os.environ,
        "NO_COLOR": "1",
        "PYTHONUTF8": "1",
        "UV_PYTHON_DOWNLOADS": "automatic",
        **(env or {}),
    }
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=merged_env,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
    return result


def venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def assert_inside(child: Path, parent: Path, label: str) -> None:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise AssertionError(f"{label} is outside managed venv: {child}") from exc


def main() -> int:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required for the managed install smoke test")

    temp_root = Path(tempfile.mkdtemp(prefix="zk_uv_install_smoke_"))
    venv = temp_root / "venv"

    try:
        print(f"Creating uv-managed Python {PYTHON_VERSION} venv at {venv}")
        create = run([uv, "venv", str(venv), "--python", PYTHON_VERSION], timeout=300)
        if create.returncode != 0:
            return create.returncode

        python = venv_python(venv)
        if not python.exists():
            raise AssertionError(f"Managed Python not found: {python}")

        keeper_package, keeper_source = resolve_zotero_keeper_package()
        print(f"Installing real extension packages into managed venv (Zotero Keeper {KEEPER_VERSION}; {keeper_source})")
        install = run(
            [
                uv,
                "pip",
                "install",
                "--upgrade",
                "--python",
                str(python),
                keeper_package,
                PUBMED_SEARCH_PACKAGE,
                "numpy",
            ],
            env={"VIRTUAL_ENV": str(venv)},
        )
        if install.returncode != 0:
            return install.returncode

        pubmed_data = temp_root / "pubmed-data"
        workspace = temp_root / "workspace"
        pubmed_data.mkdir()
        workspace.mkdir()

        probe = run(
            [
                str(python),
                "-c",
                (
                    "import asyncio, importlib.metadata, json, sys, sysconfig, numpy; "
                    "from mcp.client import Client; "
                    "from pubmed_search.presentation.mcp_server import create_server as create_pubmed_server; "
                    "from zotero_mcp import create_server as create_zotero_server\n"
                    "async def inspect():\n"
                    "    zotero_server = create_zotero_server().mcp\n"
                    "    pubmed_server = create_pubmed_server("
                    "email='smoke@example.com', data_dir=sys.argv[1], workspace_dir=sys.argv[2])\n"
                    "    async with Client(zotero_server) as zotero_client:\n"
                    "        zotero_tools = await zotero_client.list_tools()\n"
                    "    async with Client(pubmed_server) as pubmed_client:\n"
                    "        pubmed_tools = await pubmed_client.list_tools()\n"
                    "    return {"
                    "'prefix': sys.prefix, "
                    "'base_prefix': sys.base_prefix, "
                    "'purelib': sysconfig.get_paths()['purelib'], "
                    "'numpy': numpy.__file__, "
                    "'zotero_keeper_version': importlib.metadata.version('zotero-keeper'), "
                    "'zotero_server': type(zotero_server).__name__, "
                    "'pubmed_server': type(pubmed_server).__name__, "
                    "'zotero_tools': len(zotero_tools.tools), "
                    "'pubmed_tools': len(pubmed_tools.tools), "
                    "'has_import_articles': any(t.name == 'import_articles' for t in zotero_tools.tools), "
                    "'has_authorize_local_writes': any(t.name == 'authorize_local_writes' for t in zotero_tools.tools), "
                    "'has_create_collection': any(t.name == 'create_collection' for t in zotero_tools.tools), "
                    "'has_attach_file_to_item': any(t.name == 'attach_file_to_item' for t in zotero_tools.tools), "
                    "'has_delete_item': any(t.name == 'delete_item' for t in zotero_tools.tools), "
                    "'has_replace_attachment_file': any(t.name == 'replace_attachment_file' for t in zotero_tools.tools), "
                    "'has_set_attachment_fulltexts': any(t.name == 'set_attachment_fulltexts' for t in zotero_tools.tools), "
                    "'has_unified_search': any(t.name == 'unified_search' for t in pubmed_tools.tools), "
                    "'has_chronicle': any(t.name == 'build_research_chronicle' for t in pubmed_tools.tools)"
                    "}\n"
                    "print(json.dumps(asyncio.run(inspect())))"
                ),
                str(pubmed_data),
                str(workspace),
            ],
            timeout=60,
        )
        if probe.returncode != 0:
            return probe.returncode

        import json

        data = json.loads(probe.stdout.strip())
        prefix = Path(data["prefix"])
        purelib = Path(data["purelib"])
        numpy_path = Path(data["numpy"])

        if data["prefix"] == data["base_prefix"]:
            raise AssertionError("Probe interpreter is not running inside a venv")

        assert_inside(prefix, venv, "sys.prefix")
        assert_inside(purelib, venv, "site-packages")
        assert_inside(numpy_path, venv, "numpy")

        if data["zotero_keeper_version"] != KEEPER_VERSION:
            raise AssertionError(
                "Managed install resolved the wrong Zotero Keeper metadata version: "
                f"expected {KEEPER_VERSION}, got {data['zotero_keeper_version']}; "
                f"source={keeper_source}"
            )
        if data["zotero_server"] != "MCPServer" or data["pubmed_server"] != "MCPServer":
            raise AssertionError(f"SDK v2 MCPServer not used by both packages: {data}")
        required_keeper_surface = (
            data["has_import_articles"]
            and data["has_authorize_local_writes"]
            and data["has_create_collection"]
            and data["has_attach_file_to_item"]
            and data["has_delete_item"]
            and data["has_replace_attachment_file"]
            and data["has_set_attachment_fulltexts"]
        )
        if data["zotero_tools"] != 41 or not required_keeper_surface:
            raise AssertionError(f"Unexpected Zotero Keeper tool surface: {data}")
        if data["pubmed_tools"] != 45 or not data["has_unified_search"] or not data["has_chronicle"]:
            raise AssertionError(f"Unexpected PubMed Search MCP tool surface: {data}")

        system_purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
        if system_purelib == purelib.resolve():
            raise AssertionError(f"Managed install reused system site-packages: {system_purelib}")

        print("Managed uv package install smoke passed.")
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
