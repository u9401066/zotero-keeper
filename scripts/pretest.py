#!/usr/bin/env python3
"""Local pre-test gate: everything deterministic runs here, not in GitHub Actions.

GitHub CI keeps only checks that cannot be reproduced on a developer machine
(clean checkout/lockfile install, Windows/Linux runtime behavior, the release
tag archive, publishing). Run this before pushing:

    python scripts/pretest.py            # guards + Keeper + extension (fast)
    python scripts/pretest.py --full     # + VSIX packaging/inspection + managed install smoke
    python scripts/pretest.py --only keeper --keep-going

Standard library only; it shells out to uv and npm.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEPER = ROOT / "mcp-server"
EXTENSION = ROOT / "vscode-extension"


@dataclass(frozen=True)
class Step:
    group: str
    name: str
    cwd: Path
    command: tuple[str, ...]
    full_only: bool = False


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"pretest: required tool '{name}' was not found on PATH")
    return path


def _powershell() -> str:
    return shutil.which("pwsh") or shutil.which("powershell") or _tool("pwsh")


def build_steps() -> list[Step]:
    uv, npm = _tool("uv"), _tool("npm")
    return [
        Step(
            "guards",
            "no pip usage",
            ROOT,
            (uv, "run", "python", "scripts/check_no_pip.py"),
        ),
        Step(
            "guards",
            "version sync",
            ROOT,
            (uv, "run", "python", "scripts/check_version_sync.py"),
        ),
        Step(
            "guards",
            "assistant skills",
            ROOT,
            (uv, "run", "--with", "pyyaml", "python", "scripts/check_cline_skills.py"),
        ),
        Step(
            "guards",
            "collaboration-safe docs",
            KEEPER,
            (uv, "run", "python", "../scripts/check_collaboration_safe_docs.py"),
        ),
        Step(
            "keeper", "ruff lint", KEEPER, (uv, "run", "ruff", "check", "src", "tests")
        ),
        Step(
            "keeper",
            "ruff format",
            KEEPER,
            (uv, "run", "ruff", "format", "--check", "src", "tests"),
        ),
        Step("keeper", "mypy", KEEPER, (uv, "run", "mypy", "src")),
        Step("keeper", "pytest (unit + smoke)", KEEPER, (uv, "run", "pytest", "-q")),
        Step(
            "keeper",
            "MCP surface check",
            KEEPER,
            (uv, "run", "python", "tests/check_mcp.py"),
        ),
        Step(
            "extension",
            "assets in sync (read-only)",
            EXTENSION,
            (npm, "run", "sync-assets:check"),
        ),
        Step("extension", "compile + lint + mocha", EXTENSION, (npm, "test")),
        Step(
            "extension",
            "package VSIX",
            EXTENSION,
            (npm, "run", "package"),
            full_only=True,
        ),
        Step(
            "extension",
            "inspect VSIX",
            EXTENSION,
            (
                _powershell(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "./scripts/check-vsix-contents.ps1",
            ),
            full_only=True,
        ),
        Step(
            "extension",
            "managed uv install smoke",
            EXTENSION,
            (uv, "run", "python", "tests/test_uv_managed_install_smoke.py"),
            full_only=True,
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="also package/inspect the VSIX and run the managed install smoke (network)",
    )
    parser.add_argument(
        "--only",
        choices=["guards", "keeper", "extension"],
        action="append",
        help="run only these groups",
    )
    parser.add_argument(
        "--keep-going", action="store_true", help="continue after a failing step"
    )
    parser.add_argument("--list", action="store_true", help="print the steps and exit")
    args = parser.parse_args(argv)

    steps = [
        s
        for s in build_steps()
        if (args.full or not s.full_only) and (not args.only or s.group in args.only)
    ]
    if args.list:
        for step in steps:
            print(f"[{step.group}] {step.name}: {' '.join(step.command)}")
        return 0

    results: list[tuple[Step, int, float]] = []
    for step in steps:
        print(f"\n=== [{step.group}] {step.name} ===", flush=True)
        started = time.monotonic()
        code = subprocess.run(step.command, cwd=step.cwd, check=False).returncode
        results.append((step, code, time.monotonic() - started))
        if code and not args.keep_going:
            break

    print("\n=== pretest summary ===")
    for step, code, seconds in results:
        print(
            f"{'PASS' if code == 0 else 'FAIL'}  {seconds:6.1f}s  [{step.group}] {step.name}"
        )
    skipped = len(steps) - len(results)
    if skipped:
        print(
            f"(stopped early; {skipped} step(s) not run - use --keep-going to continue)"
        )
    failed = [step.name for step, code, _ in results if code]
    if failed:
        print(f"pretest FAILED: {', '.join(failed)}")
        return 1
    print("pretest passed - safe to push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
