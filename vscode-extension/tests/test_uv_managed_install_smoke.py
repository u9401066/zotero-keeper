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


PYTHON_VERSION = "3.12"
REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER = REPO_ROOT / "mcp-server"
PUBMED_SEARCH_FIXED_COMMIT = (
    "13292cb91215cff707a4380e955967e5e9b3e765"  # pragma: allowlist secret
)
PUBMED_SEARCH_PACKAGE = (
    "pubmed-search-mcp @ "
    f"https://github.com/u9401066/pubmed-search-mcp/archive/{PUBMED_SEARCH_FIXED_COMMIT}.tar.gz"
)


def run(
    cmd: list[str], timeout: int = 600, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
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

        print("Installing real extension packages into managed venv")
        install = run(
            [
                uv,
                "pip",
                "install",
                "--upgrade",
                "--python",
                str(python),
                str(MCP_SERVER),
                PUBMED_SEARCH_PACKAGE,
                "numpy",
            ],
            env={"VIRTUAL_ENV": str(venv)},
        )
        if install.returncode != 0:
            return install.returncode

        probe = run(
            [
                str(python),
                "-c",
                (
                    "import json, sys, sysconfig, zotero_mcp, pubmed_search, numpy; "
                    "print(json.dumps({"
                    "'prefix': sys.prefix, "
                    "'base_prefix': sys.base_prefix, "
                    "'purelib': sysconfig.get_paths()['purelib'], "
                    "'numpy': numpy.__file__"
                    "}))"
                ),
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

        system_purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
        if system_purelib == purelib.resolve():
            raise AssertionError(
                f"Managed install reused system site-packages: {system_purelib}"
            )

        print("Managed uv package install smoke passed.")
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
