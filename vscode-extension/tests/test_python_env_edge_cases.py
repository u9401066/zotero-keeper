#!/usr/bin/env python3
"""
UvPythonManager Edge Case Test Suite
=====================================
Tests various installation scenarios that users may encounter:

A. Fresh Install
B. System Python conflicts
C. Target location conflicts (existing venv, different Python, corrupted)
D. Package management (outdated, missing, reinstall)
E. Cleanup & reinstall
F. Concurrent access
G. uv binary issues
H. Version check accuracy

Usage:
    python test_python_env_edge_cases.py
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
import json
from pathlib import Path
from typing import Optional

# ======================================================================
# Configuration
# ======================================================================
UV_VERSION = '0.5.14'
PYTHON_VERSION = '3.12'
REQUIRED_PACKAGES = [
    'zotero-keeper>=1.11.0',
    'pubmed-search-mcp>=0.3.8',
]

# Test directory - use temp
TEST_BASE = Path(tempfile.mkdtemp(prefix='uvpy_test_'))
RESULTS: list[dict] = []


def _safe_print(msg: str):
    """Print with fallback for cp950/non-UTF8 terminals."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))


def log(msg: str, level: str = "INFO"):
    icon = {"INFO": "[i]", "OK": "[+]", "FAIL": "[-]", "WARN": "[!]", "TEST": "[T]"}.get(level, "")
    _safe_print(f"  {icon} [{level}] {msg}")


def record(test_name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    icon = "[PASS]" if passed else "[FAIL]"
    _safe_print(f"\n{icon} {test_name}")
    if detail:
        _safe_print(f"   -> {detail}")


# ======================================================================
# Helper: Find or get uv
# ======================================================================
def get_uv_path() -> str:
    """Find uv in PATH or download it."""
    try:
        result = subprocess.run(['where', 'uv'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            uv = result.stdout.strip().split('\n')[0].strip()
            log(f"Found uv at: {uv}")
            return uv
    except Exception:
        pass
    
    # Try uv directly
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return 'uv'
    except Exception:
        pass
    
    raise RuntimeError("uv not found. Please install uv first.")


def run_cmd(cmd: list[str], env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a command with timeout and return result."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
    )


# ======================================================================
# Test Scenarios
# ======================================================================

class TestPythonEnvEdgeCases:
    """Test all edge cases for UvPythonManager."""
    
    def __init__(self):
        self.uv = get_uv_path()
        self.test_dir = TEST_BASE
        
    def _make_scenario_dir(self, name: str) -> Path:
        """Create a clean scenario directory."""
        d = self.test_dir / name
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        return d
    
    def _get_python_in_venv(self, venv_dir: Path) -> Path:
        """Get Python binary path inside a venv."""
        if sys.platform == 'win32':
            return venv_dir / 'Scripts' / 'python.exe'
        return venv_dir / 'bin' / 'python'
    
    def _create_venv(self, venv_dir: Path) -> bool:
        """Create venv using uv."""
        result = run_cmd(
            [self.uv, 'venv', str(venv_dir), '--python', PYTHON_VERSION],
            env={'UV_PYTHON_DOWNLOADS': 'automatic'},
            timeout=300,
        )
        return result.returncode == 0
    
    def _install_packages(self, venv_dir: Path, packages: list[str]) -> tuple[bool, str]:
        """Install packages into venv using uv."""
        python = str(self._get_python_in_venv(venv_dir))
        for pkg in packages:
            result = run_cmd(
                [self.uv, 'pip', 'install', '--upgrade', '--python', python, pkg],
                env={'VIRTUAL_ENV': str(venv_dir)},
                timeout=300,
            )
            if result.returncode != 0:
                return False, f"Failed to install {pkg}: {result.stderr}"
        return True, ""
    
    def _check_package_version(self, venv_dir: Path, import_name: str) -> Optional[str]:
        """Check a package's __version__ in a venv."""
        python = str(self._get_python_in_venv(venv_dir))
        result = run_cmd(
            [python, '-c', f'import {import_name}; print(getattr({import_name}, "__version__", "NONE"))'],
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def _check_installed_version_via_pip(self, venv_dir: Path, pkg_name: str) -> Optional[str]:
        """Check installed version using uv pip show."""
        python = str(self._get_python_in_venv(venv_dir))
        result = run_cmd(
            [self.uv, 'pip', 'show', '--python', python, pkg_name],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=30,
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        return None

    # ------------------------------------------------------------------
    # A. Fresh Install
    # ------------------------------------------------------------------
    def test_A1_fresh_install(self):
        """A1: Complete fresh install - no uv, no venv."""
        print("\n" + "="*60)
        print("A1: Fresh Install (no pre-existing Python/venv)")
        print("="*60)
        
        d = self._make_scenario_dir("A1_fresh")
        venv_dir = d / 'venv'
        
        # Step 1: Create venv (uv will download Python if needed)
        log("Creating venv with uv...")
        ok = self._create_venv(venv_dir)
        if not ok:
            record("A1_fresh_install", False, "Failed to create venv")
            return
        
        python = self._get_python_in_venv(venv_dir)
        if not python.exists():
            record("A1_fresh_install", False, f"Python not found at {python}")
            return
        
        log(f"Python created at: {python}")
        
        # Step 2: Install packages
        log("Installing packages...")
        ok, err = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        if not ok:
            record("A1_fresh_install", False, err)
            return
        
        # Step 3: Verify imports work
        log("Verifying imports...")
        for mod in ['zotero_mcp', 'pubmed_search']:
            ver = self._check_package_version(venv_dir, mod)
            if ver is None:
                record("A1_fresh_install", False, f"Cannot import {mod}")
                return
            log(f"  {mod} version: {ver}")
        
        record("A1_fresh_install", True)

    # ------------------------------------------------------------------
    # B. System Python Conflicts
    # ------------------------------------------------------------------
    def test_B1_system_python_exists(self):
        """B1: System Python exists on PATH - uv should create separate venv."""
        print("\n" + "="*60)
        print("B1: System Python exists on PATH")
        print("="*60)
        
        # Check system Python
        try:
            result = run_cmd([sys.executable, '--version'])
            sys_ver = result.stdout.strip()
            log(f"System Python: {sys_ver} at {sys.executable}")
        except Exception:
            log("No system Python found, skipping", "WARN")
            record("B1_system_python_coexist", True, "Skipped - no system Python")
            return
        
        d = self._make_scenario_dir("B1_system_conflict")
        venv_dir = d / 'venv'
        
        # Create uv-managed venv
        ok = self._create_venv(venv_dir)
        if not ok:
            record("B1_system_python_coexist", False, "Failed to create venv")
            return
        
        uv_python = self._get_python_in_venv(venv_dir)
        
        # Verify uv-managed Python is different from system Python
        result = run_cmd([str(uv_python), '-c', 'import sys; print(sys.executable)'])
        uv_executable = result.stdout.strip()
        
        log(f"System Python: {sys.executable}")
        log(f"UV Python:     {uv_executable}")
        
        # They should be different paths
        is_different = os.path.normpath(uv_executable) != os.path.normpath(sys.executable)
        record("B1_system_python_coexist", is_different,
               f"UV Python is {'separate from' if is_different else 'SAME AS'} system Python")

    def test_B2_old_system_python(self):
        """B2: System has old Python (3.8/3.9) - uv should still get 3.12."""
        print("\n" + "="*60)
        print("B2: uv should get Python 3.12 regardless of system version")
        print("="*60)
        
        d = self._make_scenario_dir("B2_old_python")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("B2_correct_python_version", False, "Failed to create venv")
            return
        
        uv_python = self._get_python_in_venv(venv_dir)
        result = run_cmd([str(uv_python), '--version'])
        version = result.stdout.strip()
        log(f"Python version in venv: {version}")
        
        # Should be 3.12.x
        is_312 = 'Python 3.12' in version
        record("B2_correct_python_version", is_312,
               f"Got {version}, expected Python 3.12.x")

    # ------------------------------------------------------------------
    # C. Target Location Conflicts
    # ------------------------------------------------------------------
    def test_C1_venv_dir_exists_empty(self):
        """C1: Venv directory exists but is empty."""
        print("\n" + "="*60)
        print("C1: Existing but empty venv directory")
        print("="*60)
        
        d = self._make_scenario_dir("C1_empty_dir")
        venv_dir = d / 'venv'
        venv_dir.mkdir(parents=True, exist_ok=True)
        
        log(f"Created empty dir at: {venv_dir}")
        
        ok = self._create_venv(venv_dir)
        python = self._get_python_in_venv(venv_dir)
        
        record("C1_empty_venv_dir", ok and python.exists(),
               f"uv venv on empty dir: {'OK' if ok else 'FAILED'}")

    def test_C2_venv_exists_with_different_python(self):
        """C2: Venv exists with Python 3.11, we want 3.12."""
        print("\n" + "="*60)
        print("C2: Existing venv with wrong Python version")
        print("="*60)
        
        d = self._make_scenario_dir("C2_wrong_python")
        venv_dir = d / 'venv'
        
        # First create with 3.11
        log("Creating venv with Python 3.11...")
        result = run_cmd(
            [self.uv, 'venv', str(venv_dir), '--python', '3.11'],
            env={'UV_PYTHON_DOWNLOADS': 'automatic'},
            timeout=300,
        )
        if result.returncode != 0:
            log(f"Could not create 3.11 venv: {result.stderr}", "WARN")
            record("C2_overwrite_wrong_python", True, "Skipped - 3.11 not available")
            return
        
        python = self._get_python_in_venv(venv_dir)
        r1 = run_cmd([str(python), '--version'])
        log(f"Before: {r1.stdout.strip()}")
        
        # Now overwrite with 3.12
        log("Overwriting with Python 3.12...")
        ok = self._create_venv(venv_dir)
        
        r2 = run_cmd([str(python), '--version'])
        log(f"After:  {r2.stdout.strip()}")
        
        is_312 = 'Python 3.12' in r2.stdout
        record("C2_overwrite_wrong_python", ok and is_312,
               f"After overwrite: {r2.stdout.strip()}")

    def test_C3_corrupted_python_binary(self):
        """C3: Python binary exists but is corrupted."""
        print("\n" + "="*60)
        print("C3: Corrupted Python binary in venv")
        print("="*60)
        
        d = self._make_scenario_dir("C3_corrupt")
        venv_dir = d / 'venv'
        
        # Create valid venv first
        ok = self._create_venv(venv_dir)
        if not ok:
            record("C3_corrupted_python", False, "Cannot create base venv")
            return
        
        python = self._get_python_in_venv(venv_dir)
        
        # Corrupt the binary
        log("Corrupting Python binary...")
        with open(python, 'wb') as f:
            f.write(b'\x00\x00\x00CORRUPTED')
        
        # Verify it's broken (on Windows, running corrupted exe gives WinError 216)
        try:
            result = run_cmd([str(python), '--version'])
            is_broken = result.returncode != 0
        except (OSError, subprocess.SubprocessError):
            is_broken = True
        log(f"Corrupted binary is broken: {is_broken} (should be True)")
        
        # Extension's checkReadySync AFTER FIX: should detect corruption
        # (now tries to run python --version, not just check file existence)
        exists = python.exists()
        log(f"File exists: {exists} (binary is there but broken)")
        
        # Simulate fixed checkReadySync: try to run it
        try:
            result = run_cmd([str(python), '--version'])
            reports_python = result.returncode == 0 and result.stdout.strip().startswith('Python')
        except (OSError, subprocess.SubprocessError):
            reports_python = False
        log(f"Fixed checkReadySync would report ready: {reports_python} (should be False)")
        
        # Now try to re-create venv (what setup() does after corrupted detection)
        log("Re-creating venv over corrupted one...")
        ok = self._create_venv(venv_dir)
        
        try:
            result = run_cmd([str(python), '--version'])
            fixed = result.returncode == 0 and 'Python 3.12' in result.stdout
        except (OSError, subprocess.SubprocessError):
            fixed = False
        
        record("C3_corrupted_python", is_broken and not reports_python and fixed,
               f"Corrupted detected: {is_broken}, "
               f"Fixed check blocks it: {not reports_python}, "
               f"Recreate fixed it: {fixed}")

    def test_C4_venv_exists_packages_missing(self):
        """C4: Valid venv but packages not installed."""
        print("\n" + "="*60)
        print("C4: Valid venv, missing packages")
        print("="*60)
        
        d = self._make_scenario_dir("C4_no_packages")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("C4_missing_packages_detect", False, "Cannot create venv")
            return
        
        python = self._get_python_in_venv(venv_dir)
        
        # Try importing without packages installed
        result = run_cmd([str(python), '-c', 'import zotero_mcp'])
        can_import = result.returncode == 0
        log(f"Import zotero_mcp without install: {can_import} (should be False)")
        
        # Now install
        log("Installing packages...")
        ok, err = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        if not ok:
            record("C4_missing_packages_detect", False, err)
            return
        
        result = run_cmd([str(python), '-c', 'import zotero_mcp'])
        can_import_after = result.returncode == 0
        
        record("C4_missing_packages_detect", not can_import and can_import_after,
               f"Before install: import={can_import}, After: import={can_import_after}")

    def test_C5_partial_venv_structure(self):
        """C5: Venv directory exists with partial structure (no python binary)."""
        print("\n" + "="*60)
        print("C5: Partial venv structure (missing python binary)")
        print("="*60)
        
        d = self._make_scenario_dir("C5_partial")
        venv_dir = d / 'venv'
        
        # Create partial structure
        if sys.platform == 'win32':
            (venv_dir / 'Scripts').mkdir(parents=True, exist_ok=True)
            # Create pyvenv.cfg to look like a real venv
            (venv_dir / 'pyvenv.cfg').write_text('home = C:\\fake\\path\n')
        else:
            (venv_dir / 'bin').mkdir(parents=True, exist_ok=True)
            (venv_dir / 'pyvenv.cfg').write_text('home = /fake/path\n')
        
        python = self._get_python_in_venv(venv_dir)
        log(f"Python binary exists: {python.exists()} (should be False)")
        
        # uv venv should handle this
        log("Running uv venv on partial structure...")
        ok = self._create_venv(venv_dir)
        
        record("C5_partial_venv_recovery", ok and python.exists(),
               f"uv venv recovered partial venv: {ok and python.exists()}")

    # ------------------------------------------------------------------
    # D. Package Management
    # ------------------------------------------------------------------
    def test_D1_packages_outdated(self):
        """D1: Packages installed but versions outdated."""
        print("\n" + "="*60)
        print("D1: Outdated package versions")
        print("="*60)
        
        d = self._make_scenario_dir("D1_outdated")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("D1_upgrade_outdated", False, "Cannot create venv")
            return
        
        python = self._get_python_in_venv(venv_dir)
        
        # Install an older version first (if possible)
        log("Installing older version of zotero-keeper...")
        result = run_cmd(
            [self.uv, 'pip', 'install', '--python', str(python), 'zotero-keeper==1.10.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        
        if result.returncode != 0:
            log(f"Could not install older version: {result.stderr}", "WARN")
            # Try any version
            result = run_cmd(
                [self.uv, 'pip', 'install', '--python', str(python), 'zotero-keeper'],
                env={'VIRTUAL_ENV': str(venv_dir)},
                timeout=120,
            )
        
        ver_before = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        log(f"Version before upgrade: {ver_before}")
        
        # Upgrade with version constraint
        log("Upgrading with version constraint...")
        result = run_cmd(
            [self.uv, 'pip', 'install', '--upgrade', '--python', str(python), 'zotero-keeper>=1.11.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        
        ver_after = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        log(f"Version after upgrade: {ver_after}")
        
        record("D1_upgrade_outdated", result.returncode == 0,
               f"Upgrade: {ver_before} → {ver_after}")

    def test_D2_package_uninstall_reinstall(self):
        """D2: Package uninstalled, then reinstalled."""
        print("\n" + "="*60)
        print("D2: Package uninstall then reinstall")
        print("="*60)
        
        d = self._make_scenario_dir("D2_reinstall")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("D2_uninstall_reinstall", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # Install
        log("Installing zotero-keeper...")
        run_cmd(
            [self.uv, 'pip', 'install', '--python', python, 'zotero-keeper>=1.11.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        
        ver1 = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        log(f"Installed version: {ver1}")
        
        # Uninstall
        log("Uninstalling...")
        result = run_cmd(
            [self.uv, 'pip', 'uninstall', '--python', python, 'zotero-keeper'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=30,
        )
        
        ver2 = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        log(f"After uninstall: {ver2}")
        
        # Reinstall (what upgradePackages does)
        log("Reinstalling with --upgrade...")
        result = run_cmd(
            [self.uv, 'pip', 'install', '--upgrade', '--python', python, 'zotero-keeper>=1.11.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        
        ver3 = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        log(f"After reinstall: {ver3}")
        
        record("D2_uninstall_reinstall", ver3 is not None,
               f"Install → Uninstall → Reinstall: {ver1} → {ver2} → {ver3}")

    def test_D3_version_check_accuracy(self):
        """D3: CRITICAL - Test __version__ vs installed version mismatch.
        
        After fix: Extension now uses importlib.metadata.version() instead of __version__.
        """
        print("\n" + "="*60)
        print("D3: importlib.metadata version check (FIXED)")
        print("="*60)
        
        d = self._make_scenario_dir("D3_version_mismatch")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("D3_version_check_accuracy", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # Install packages
        ok, err = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        if not ok:
            record("D3_version_check_accuracy", False, err)
            return
        
        # Also install packaging
        run_cmd(
            [self.uv, 'pip', 'install', '--python', python, 'packaging'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=60,
        )
        
        # Check __version__ vs importlib.metadata.version vs pip show
        issues = []
        all_ok = True
        for pkg_name, import_name, min_ver in [
            ('zotero-keeper', 'zotero_mcp', '1.11.0'),
            ('pubmed-search-mcp', 'pubmed_search', '0.3.8'),
        ]:
            attr_ver = self._check_package_version(venv_dir, import_name)
            pip_ver = self._check_installed_version_via_pip(venv_dir, pkg_name)
            
            # Check importlib.metadata version (the FIXED approach)
            meta_result = run_cmd([
                python, '-c',
                f'from importlib.metadata import version; print(version("{pkg_name}"))'
            ])
            meta_ver = meta_result.stdout.strip() if meta_result.returncode == 0 else None
            
            log(f"{pkg_name}:")
            log(f"  __version__ attr:     {attr_ver}")
            log(f"  importlib.metadata:   {meta_ver}")
            log(f"  pip show:             {pip_ver}")
            log(f"  min required:         {min_ver}")
            
            if attr_ver != pip_ver:
                log(f"  [INFO] __version__ mismatch (known issue, no longer used)", "WARN")
            
            if meta_ver != pip_ver:
                issues.append(f"importlib.metadata({meta_ver}) != pip({pip_ver}) for {pkg_name}")
                all_ok = False
            
            # Simulate the FIXED extension version check
            result = run_cmd([
                python, '-c',
                f'from packaging.version import Version; '
                f'from importlib.metadata import version as get_version; '
                f'v = get_version("{pkg_name}"); '
                f'print("OK" if Version(v) >= Version("{min_ver}") else f"OUTDATED:{{v}}")'
            ])
            ver_check_result = result.stdout.strip()
            log(f"  Fixed version check:  {ver_check_result}")
            
            if 'OUTDATED' in ver_check_result:
                issues.append(f"Fixed check still reports OUTDATED for {pkg_name}: {ver_check_result}")
                all_ok = False
        
        if issues:
            record("D3_version_check_accuracy", False, " | ".join(issues))
        else:
            record("D3_version_check_accuracy", True,
                   "importlib.metadata matches pip versions, fixed check reports OK")

    def test_D4_already_latest_upgrade(self):
        """D4: Package already at latest - upgrade should be a no-op."""
        print("\n" + "="*60)
        print("D4: Upgrading already-latest package")
        print("="*60)
        
        d = self._make_scenario_dir("D4_latest")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("D4_already_latest", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # Install
        run_cmd(
            [self.uv, 'pip', 'install', '--upgrade', '--python', python, 'zotero-keeper>=1.11.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        ver1 = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        
        # Upgrade again (should be quick no-op)
        start = time.time()
        result = run_cmd(
            [self.uv, 'pip', 'install', '--upgrade', '--python', python, 'zotero-keeper>=1.11.0'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        elapsed = time.time() - start
        ver2 = self._check_installed_version_via_pip(venv_dir, 'zotero-keeper')
        
        log(f"Version before: {ver1}, after: {ver2}")
        log(f"Upgrade elapsed: {elapsed:.1f}s (should be fast)")
        
        record("D4_already_latest", result.returncode == 0 and ver1 == ver2,
               f"No-op upgrade took {elapsed:.1f}s, version unchanged: {ver1} → {ver2}")

    # ------------------------------------------------------------------
    # E. Cleanup & Reinstall
    # ------------------------------------------------------------------
    def test_E1_cleanup_and_reinstall(self):
        """E1: Full cleanup then reinstall."""
        print("\n" + "="*60)
        print("E1: Cleanup → Reinstall cycle")
        print("="*60)
        
        d = self._make_scenario_dir("E1_reinstall")
        venv_dir = d / 'venv'
        
        # First install
        log("Initial install...")
        ok = self._create_venv(venv_dir)
        if not ok:
            record("E1_cleanup_reinstall", False, "Cannot create initial venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        ok, _ = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        
        # Cleanup (simulating uvPython.cleanup())
        log("Cleaning up (removing venv dir)...")
        shutil.rmtree(venv_dir, ignore_errors=True)
        
        exists_after_cleanup = Path(python).exists()
        log(f"Python after cleanup: {exists_after_cleanup} (should be False)")
        
        # Reinstall
        log("Reinstalling...")
        ok = self._create_venv(venv_dir)
        if not ok:
            record("E1_cleanup_reinstall", False, "Reinstall failed")
            return
        
        ok, err = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        exists_after_reinstall = Path(python).exists()
        
        record("E1_cleanup_reinstall", 
               not exists_after_cleanup and exists_after_reinstall and ok,
               f"Cleanup removed Python: {not exists_after_cleanup}, Reinstall worked: {exists_after_reinstall}")

    def test_E2_cleanup_nonexistent(self):
        """E2: Cleanup when nothing exists (should not throw)."""
        print("\n" + "="*60)
        print("E2: Cleanup on non-existent directory")
        print("="*60)
        
        d = self._make_scenario_dir("E2_no_cleanup")
        venv_dir = d / 'venv'
        
        # Don't create anything, just try to remove
        try:
            if venv_dir.exists():
                shutil.rmtree(venv_dir)
            log("Cleanup on non-existent dir: no error")
            passed = True
        except Exception as e:
            log(f"Error during cleanup: {e}", "FAIL")
            passed = False
        
        record("E2_cleanup_nonexistent", passed)

    # ------------------------------------------------------------------
    # F. uv binary issues
    # ------------------------------------------------------------------
    def test_F1_uv_overwrite_existing_venv(self):
        """F1: uv venv should overwrite an existing venv safely."""
        print("\n" + "="*60)
        print("F1: uv venv --python 3.12 on existing venv (overwrite)")
        print("="*60)
        
        d = self._make_scenario_dir("F1_overwrite")
        venv_dir = d / 'venv'
        
        # Create first
        log("Creating initial venv...")
        ok = self._create_venv(venv_dir)
        if not ok:
            record("F1_uv_overwrite_venv", False, "Cannot create initial venv")
            return
        
        # Install a package to verify it gets reset
        python = str(self._get_python_in_venv(venv_dir))
        run_cmd(
            [self.uv, 'pip', 'install', '--python', python, 'packaging'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=60,
        )
        
        has_pkg_before = run_cmd([python, '-c', 'import packaging']).returncode == 0
        log(f"packaging installed before overwrite: {has_pkg_before}")
        
        # Overwrite
        log("Overwriting venv...")
        ok = self._create_venv(venv_dir)
        python = str(self._get_python_in_venv(venv_dir))
        
        # After overwrite, the venv should be fresh (no packages)
        has_pkg_after = run_cmd([python, '-c', 'import packaging']).returncode == 0
        log(f"packaging installed after overwrite: {has_pkg_after}")
        
        # uv venv may or may not clear packages. Document behavior.
        record("F1_uv_overwrite_venv", ok,
               f"Before overwrite: packaging={has_pkg_before}, After: packaging={has_pkg_after}. "
               f"{'Venv was reset' if not has_pkg_after else 'Venv preserved packages (uv keeps site-packages)'}")

    # ------------------------------------------------------------------
    # G. Version check script edge cases
    # ------------------------------------------------------------------
    def test_G1_version_check_no_packaging(self):
        """G1: Version check when 'packaging' module is not installed."""
        print("\n" + "="*60)
        print("G1: Version check without 'packaging' module")
        print("="*60)
        
        d = self._make_scenario_dir("G1_no_packaging")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("G1_no_packaging", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # The extension's version check script
        version_check_script = '''
import sys
try:
    from packaging.version import Version
except ImportError:
    print("NEED_PACKAGING")
    sys.exit(0)
print("HAS_PACKAGING")
'''
        script_path = str(d / 'check.py')
        with open(script_path, 'w') as f:
            f.write(version_check_script)
        
        result = run_cmd([python, script_path])
        output = result.stdout.strip()
        log(f"Result without packaging: {output}")
        
        # Extension handles NEED_PACKAGING → returns false → triggers install
        record("G1_no_packaging", output == "NEED_PACKAGING",
               f"Expected NEED_PACKAGING, got: {output}")

    def test_G2_version_check_missing_module(self):
        """G2: Version check when a required module is missing."""
        print("\n" + "="*60)
        print("G2: Version check with missing module")
        print("="*60)
        
        d = self._make_scenario_dir("G2_missing_mod")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("G2_missing_module", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # Install packaging but not the actual packages
        run_cmd(
            [self.uv, 'pip', 'install', '--python', python, 'packaging'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=60,
        )
        
        version_check_script = '''
import sys
try:
    from packaging.version import Version
except ImportError:
    print("NEED_PACKAGING")
    sys.exit(0)
try:
    import zotero_mcp
    import pubmed_search
except ImportError as e:
    print(f"MISSING:{e}")
    sys.exit(0)
print("OK")
'''
        script_path = str(d / 'check.py')
        with open(script_path, 'w') as f:
            f.write(version_check_script)
        
        result = run_cmd([python, script_path])
        output = result.stdout.strip()
        log(f"Result with missing modules: {output}")
        
        record("G2_missing_module", output.startswith("MISSING:"),
               f"Expected MISSING:..., got: {output}")

    # ------------------------------------------------------------------
    # H. Idempotency & Resilience 
    # ------------------------------------------------------------------
    def test_H1_double_install_packages(self):
        """H1: Installing packages twice should not cause issues."""
        print("\n" + "="*60)
        print("H1: Double package install (idempotency)")
        print("="*60)
        
        d = self._make_scenario_dir("H1_double_install")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("H1_double_install", False, "Cannot create venv")
            return
        
        # Install twice
        log("First install...")
        ok1, _ = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        
        log("Second install...")
        ok2, _ = self._install_packages(venv_dir, REQUIRED_PACKAGES)
        
        # Both should succeed
        ver = self._check_package_version(venv_dir, 'zotero_mcp')
        
        record("H1_double_install", ok1 and ok2,
               f"First install: {ok1}, Second install: {ok2}, version: {ver}")

    def test_H2_concurrent_venv_creation(self):
        """H2: Check that concurrent venv creation is handled."""
        print("\n" + "="*60)
        print("H2: Rapid consecutive venv creation")
        print("="*60)
        
        d = self._make_scenario_dir("H2_concurrent")
        venv_dir = d / 'venv'
        
        # Create twice rapidly
        log("First creation...")
        ok1 = self._create_venv(venv_dir)
        log("Second creation (immediate)...")
        ok2 = self._create_venv(venv_dir)
        
        python = self._get_python_in_venv(venv_dir)
        result = run_cmd([str(python), '--version'])
        
        record("H2_rapid_venv_creation", ok1 and ok2 and result.returncode == 0,
               f"Create1: {ok1}, Create2: {ok2}, Python works: {result.returncode == 0}")

    def test_H3_install_with_network_package(self):
        """H3: Verify that upgrading from PyPI works correctly with fixed version check."""
        print("\n" + "="*60)
        print("H3: Live PyPI upgrade + fixed version check")
        print("="*60)
        
        d = self._make_scenario_dir("H3_pypi")
        venv_dir = d / 'venv'
        
        ok = self._create_venv(venv_dir)
        if not ok:
            record("H3_pypi_upgrade", False, "Cannot create venv")
            return
        
        python = str(self._get_python_in_venv(venv_dir))
        
        # Install pubmed-search-mcp with --upgrade (what the extension does)
        log("Installing pubmed-search-mcp with --upgrade...")
        result = run_cmd(
            [self.uv, 'pip', 'install', '--upgrade', '--python', python, 'pubmed-search-mcp>=0.3.8'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=120,
        )
        
        # Install packaging for version check
        run_cmd(
            [self.uv, 'pip', 'install', '--python', python, 'packaging'],
            env={'VIRTUAL_ENV': str(venv_dir)},
            timeout=60,
        )
        
        pip_ver = self._check_installed_version_via_pip(venv_dir, 'pubmed-search-mcp')
        attr_ver = self._check_package_version(venv_dir, 'pubmed_search')
        
        # Check importlib.metadata version (our fix)
        meta_result = run_cmd([
            python, '-c',
            'from importlib.metadata import version; print(version("pubmed-search-mcp"))'
        ])
        meta_ver = meta_result.stdout.strip() if meta_result.returncode == 0 else None
        
        log(f"pip show version:        {pip_ver}")
        log(f"__version__ attr:        {attr_ver}")
        log(f"importlib.metadata:      {meta_ver}")
        
        is_ok = pip_ver is not None and meta_ver == pip_ver
        detail = f"pip={pip_ver}, __version__={attr_ver}, metadata={meta_ver}"
        
        if attr_ver != pip_ver:
            detail += " (__version__ mismatch is KNOWN, no longer affects extension)"
        if meta_ver == pip_ver:
            detail += " | importlib.metadata CORRECT!"
        
        record("H3_pypi_upgrade", is_ok, detail)


# ======================================================================
# Main
# ======================================================================
def main():
    print("=" * 70)
    print("  UvPythonManager Edge Case Test Suite")
    print("  Testing Python env installation robustness")
    print("=" * 70)
    print(f"\nTest directory: {TEST_BASE}")
    print(f"Platform: {sys.platform}-{os.uname().machine if hasattr(os, 'uname') else 'x64'}")
    print(f"System Python: {sys.version}")
    
    tester = TestPythonEnvEdgeCases()
    
    # Run all tests
    tests = [
        tester.test_A1_fresh_install,
        tester.test_B1_system_python_exists,
        tester.test_B2_old_system_python,
        tester.test_C1_venv_dir_exists_empty,
        tester.test_C2_venv_exists_with_different_python,
        tester.test_C3_corrupted_python_binary,
        tester.test_C4_venv_exists_packages_missing,
        tester.test_C5_partial_venv_structure,
        tester.test_D1_packages_outdated,
        tester.test_D2_package_uninstall_reinstall,
        tester.test_D3_version_check_accuracy,
        tester.test_D4_already_latest_upgrade,
        tester.test_E1_cleanup_and_reinstall,
        tester.test_E2_cleanup_nonexistent,
        tester.test_F1_uv_overwrite_existing_venv,
        tester.test_G1_version_check_no_packaging,
        tester.test_G2_version_check_missing_module,
        tester.test_H1_double_install_packages,
        tester.test_H2_concurrent_venv_creation,
        tester.test_H3_install_with_network_package,
    ]
    
    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            record(test_fn.__name__, False, f"EXCEPTION: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    total = len(RESULTS)
    
    for r in RESULTS:
        icon = "[PASS]" if r['status'] == 'PASS' else "[FAIL]"
        _safe_print(f"  {icon} {r['test']}: {r['detail'][:80] if r['detail'] else ''}")
    
    _safe_print(f"\n  Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed > 0:
        _safe_print("\n  [!] FAILED TESTS REQUIRE ATTENTION!")
        for r in RESULTS:
            if r['status'] == 'FAIL':
                _safe_print(f"    [FAIL] {r['test']}")
                _safe_print(f"           {r['detail']}")
    
    # Cleanup
    print(f"\n  Test artifacts at: {TEST_BASE}")
    print(f"  Run: rmdir /s /q \"{TEST_BASE}\" to clean up")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
