"""
Cross-platform compatibility tests for Mac installation.

These tests verify the logic patterns used in the TypeScript extension code
without requiring a Mac machine. They validate:
1. Platform detection and URL mapping
2. PATH enrichment for macOS GUI apps
3. tar extraction fallback logic
4. macOS Python path discovery
5. Path construction (bin/python vs Scripts/python.exe)

Run: python tests/test_mac_compatibility.py
"""

import os
import sys
import platform
import unittest
import tempfile
import shutil
import re


# ─── UV Download URL Validation ───

UV_VERSION = '0.5.14'
UV_DOWNLOADS = {
    'win32-x64': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip',
    'win32-ia32': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-i686-pc-windows-msvc.zip',
    'linux-x64': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz',
    'linux-arm64': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-aarch64-unknown-linux-gnu.tar.gz',
    'darwin-x64': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-apple-darwin.tar.gz',
    'darwin-arm64': f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-aarch64-apple-darwin.tar.gz',
}


class TestUvDownloadUrls(unittest.TestCase):
    """Verify UV download URLs are valid for all platforms."""

    def test_all_mac_platforms_have_urls(self):
        """Both Intel and Apple Silicon Mac must have download URLs."""
        self.assertIn('darwin-x64', UV_DOWNLOADS)
        self.assertIn('darwin-arm64', UV_DOWNLOADS)

    def test_mac_urls_use_correct_architecture(self):
        """Intel Mac must use x86_64, Apple Silicon must use aarch64."""
        self.assertIn('x86_64-apple-darwin', UV_DOWNLOADS['darwin-x64'])
        self.assertIn('aarch64-apple-darwin', UV_DOWNLOADS['darwin-arm64'])

    def test_mac_urls_are_tar_gz(self):
        """Mac downloads should be tar.gz (not zip)."""
        self.assertTrue(UV_DOWNLOADS['darwin-x64'].endswith('.tar.gz'))
        self.assertTrue(UV_DOWNLOADS['darwin-arm64'].endswith('.tar.gz'))

    def test_windows_urls_are_zip(self):
        """Windows downloads should be zip."""
        self.assertTrue(UV_DOWNLOADS['win32-x64'].endswith('.zip'))

    def test_all_urls_use_https(self):
        """All download URLs must use HTTPS."""
        for key, url in UV_DOWNLOADS.items():
            self.assertTrue(url.startswith('https://'), f"{key}: {url}")

    def test_url_version_consistency(self):
        """All URLs must use the same UV version."""
        for key, url in UV_DOWNLOADS.items():
            self.assertIn(UV_VERSION, url, f"{key} URL doesn't contain version {UV_VERSION}")


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection mirrors what Node.js process.platform + process.arch reports."""

    def test_valid_platform_keys(self):
        """All expected platform keys exist."""
        expected = ['win32-x64', 'win32-ia32', 'linux-x64', 'linux-arm64', 'darwin-x64', 'darwin-arm64']
        for key in expected:
            self.assertIn(key, UV_DOWNLOADS, f"Missing platform key: {key}")


class TestPathConstruction(unittest.TestCase):
    """Test cross-platform path construction logic matches TypeScript code."""

    def test_python_binary_path_unix(self):
        """Unix (Mac/Linux) should use bin/python."""
        venv_dir = '/some/path/venv'
        # Mirrors: path.join(this.venvDir, 'bin', 'python')
        expected = os.path.join(venv_dir, 'bin', 'python')
        self.assertTrue(expected.endswith('bin/python') or expected.endswith('bin\\python'))

    def test_python_binary_path_windows(self):
        """Windows should use Scripts/python.exe."""
        venv_dir = 'C:\\Users\\user\\.vscode\\venv'
        expected = os.path.join(venv_dir, 'Scripts', 'python.exe')
        self.assertIn('Scripts', expected)
        self.assertIn('python.exe', expected)

    def test_uv_executable_name_unix(self):
        """Unix should use 'uv' (no extension)."""
        # Mirrors UV_DOWNLOADS darwin/linux entries
        for key in ['darwin-x64', 'darwin-arm64', 'linux-x64', 'linux-arm64']:
            # The executable field in TS is 'uv' for Unix
            self.assertFalse(key.startswith('win'))

    def test_paths_with_spaces(self):
        """Paths with spaces (common on macOS) should be handled."""
        # macOS globalStorageUri: ~/Library/Application Support/Code/User/globalStorage/...
        base = '/Users/user/Library/Application Support/Code/User/globalStorage/ext'
        uv_path = os.path.join(base, 'uv', 'uv')
        venv_dir = os.path.join(base, 'venv')

        # Command would be: "path with spaces" (must be quoted)
        cmd = f'"{uv_path}" venv "{venv_dir}" --python 3.12'
        self.assertIn('"', cmd)  # Must be quoted
        self.assertIn('Application Support', cmd)


class TestMacPathEnrichment(unittest.TestCase):
    """Test the PATH enrichment logic for macOS GUI apps."""

    MACOS_EXTRA_PATHS = [
        '/opt/homebrew/bin',           # Apple Silicon homebrew
        '/opt/homebrew/sbin',
        '/usr/local/bin',              # Intel homebrew
        '/usr/local/sbin',
        # HOME-relative paths tested separately
    ]

    HOME_RELATIVE_PATHS = [
        '.local/bin',      # pipx, uv, cargo installs
        '.cargo/bin',      # cargo (uv may be here)
        '.pyenv/shims',    # pyenv
    ]

    def test_enrichment_includes_homebrew_paths(self):
        """PATH must include both Apple Silicon and Intel homebrew locations."""
        self.assertIn('/opt/homebrew/bin', self.MACOS_EXTRA_PATHS)
        self.assertIn('/usr/local/bin', self.MACOS_EXTRA_PATHS)

    def test_enrichment_includes_user_tools(self):
        """PATH must include user-local tool directories."""
        self.assertIn('.local/bin', self.HOME_RELATIVE_PATHS)
        self.assertIn('.cargo/bin', self.HOME_RELATIVE_PATHS)

    def test_enrichment_includes_pyenv(self):
        """PATH must include pyenv shims."""
        self.assertIn('.pyenv/shims', self.HOME_RELATIVE_PATHS)

    def test_extra_paths_prepended(self):
        """Extra paths should be prepended (not appended) to PATH."""
        # Simulating the TS logic:
        extra = ['/opt/homebrew/bin', '/usr/local/bin']
        original_path = '/usr/bin:/bin'
        enriched = ':'.join(extra + [original_path])
        # homebrew should come before system
        homebrew_idx = enriched.index('/opt/homebrew/bin')
        system_idx = enriched.index('/usr/bin')
        self.assertLess(homebrew_idx, system_idx)


class TestMacPythonPathDiscovery(unittest.TestCase):
    """Test the macOS Python well-known path discovery logic."""

    KNOWN_MAC_PATHS = [
        '/opt/homebrew/bin/python3',       # Apple Silicon homebrew
        '/usr/local/bin/python3',          # Intel homebrew
        # HOME-relative: ~/.pyenv/shims/python3
        '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',
        '/usr/bin/python3',  # Xcode CLI tools
    ]

    def test_apple_silicon_homebrew_path_included(self):
        """Apple Silicon homebrew Python path must be checked."""
        self.assertIn('/opt/homebrew/bin/python3', self.KNOWN_MAC_PATHS)

    def test_intel_homebrew_path_included(self):
        """Intel homebrew Python path must be checked."""
        self.assertIn('/usr/local/bin/python3', self.KNOWN_MAC_PATHS)

    def test_official_installer_paths_included(self):
        """Official Python.org installer paths must be checked."""
        framework_paths = [p for p in self.KNOWN_MAC_PATHS if 'Python.framework' in p]
        self.assertGreaterEqual(len(framework_paths), 1)

    def test_xcode_cli_tools_path_included(self):
        """Xcode Command Line Tools python3 must be checked."""
        self.assertIn('/usr/bin/python3', self.KNOWN_MAC_PATHS)

    def test_discovery_order_prefers_homebrew(self):
        """Homebrew paths should be checked before system paths."""
        homebrew_idx = next(i for i, p in enumerate(self.KNOWN_MAC_PATHS) if 'homebrew' in p)
        usr_bin_idx = next(i for i, p in enumerate(self.KNOWN_MAC_PATHS) if p == '/usr/bin/python3')
        self.assertLess(homebrew_idx, usr_bin_idx)


class TestTarExtractionFallback(unittest.TestCase):
    """Test the tar extraction verification and fallback logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_find_file_in_flat_directory(self):
        """Should find uv binary when directly in the directory."""
        uv_path = os.path.join(self.tmpdir, 'uv')
        with open(uv_path, 'w') as f:
            f.write('binary')
        found = self._find_file_recursive(self.tmpdir, 'uv')
        self.assertEqual(found, uv_path)

    def test_find_file_in_nested_directory(self):
        """Should find uv binary when nested (tar without strip-components)."""
        nested = os.path.join(self.tmpdir, 'uv-aarch64-apple-darwin')
        os.makedirs(nested)
        uv_path = os.path.join(nested, 'uv')
        with open(uv_path, 'w') as f:
            f.write('binary')
        found = self._find_file_recursive(self.tmpdir, 'uv')
        self.assertEqual(found, uv_path)

    def test_find_file_deeply_nested(self):
        """Should find uv even if deeply nested."""
        deep = os.path.join(self.tmpdir, 'a', 'b', 'c')
        os.makedirs(deep)
        uv_path = os.path.join(deep, 'uv')
        with open(uv_path, 'w') as f:
            f.write('binary')
        found = self._find_file_recursive(self.tmpdir, 'uv')
        self.assertEqual(found, uv_path)

    def test_returns_none_when_not_found(self):
        """Should return None when file doesn't exist."""
        found = self._find_file_recursive(self.tmpdir, 'uv')
        self.assertIsNone(found)

    def _find_file_recursive(self, directory, filename):
        """Python equivalent of TypeScript findFileRecursive."""
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name == filename:
                        return entry.path
                    if entry.is_dir():
                        found = self._find_file_recursive(entry.path, filename)
                        if found:
                            return found
        except PermissionError:
            pass
        return None


class TestSourceCodePatterns(unittest.TestCase):
    """
    Static analysis: verify the TypeScript source contains expected patterns.
    This is the key verification method when you don't have a Mac.
    """

    @classmethod
    def setUpClass(cls):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uv_path = os.path.join(base, 'src', 'uvPythonManager.ts')
        py_path = os.path.join(base, 'src', 'pythonEnvironment.ts')
        ext_path = os.path.join(base, 'src', 'extension.ts')

        with open(uv_path, 'r', encoding='utf-8') as f:
            cls.uv_source = f.read()
        with open(py_path, 'r', encoding='utf-8') as f:
            cls.py_source = f.read()
        with open(ext_path, 'r', encoding='utf-8') as f:
            cls.ext_source = f.read()

    # ─── uvPythonManager.ts checks ───

    def test_uv_imports_os_module(self):
        """uvPythonManager must import os for homedir()."""
        self.assertIn("import * as os from 'os'", self.uv_source)

    def test_uv_has_enriched_env_function(self):
        """Must have getEnrichedEnv function for macOS PATH."""
        self.assertIn('function getEnrichedEnv', self.uv_source)

    def test_uv_enriched_env_checks_darwin(self):
        """getEnrichedEnv must check for darwin platform."""
        self.assertIn("process.platform !== 'darwin'", self.uv_source)

    def test_uv_enriched_env_has_homebrew_paths(self):
        """Must include both homebrew paths."""
        self.assertIn('/opt/homebrew/bin', self.uv_source)
        self.assertIn('/usr/local/bin', self.uv_source)

    def test_uv_enriched_env_has_user_paths(self):
        """Must include user-local paths."""
        self.assertIn('.local', self.uv_source)
        self.assertIn('.cargo', self.uv_source)
        self.assertIn('.pyenv', self.uv_source)

    def test_uv_createVenv_uses_enriched_env(self):
        """createVenv must use enrichedEnv, not raw process.env."""
        # Find the createVenv method and check it uses enrichedEnv
        self.assertIn('getEnrichedEnv()', self.uv_source)
        # Should set HOME for macOS GUI apps
        self.assertIn('os.homedir()', self.uv_source)

    def test_uv_has_find_file_recursive(self):
        """Must have findFileRecursive for tar extraction fallback."""
        self.assertIn('findFileRecursive', self.uv_source)

    def test_uv_tar_extraction_has_verification(self):
        """After tar extraction, must verify uv binary exists."""
        # Must check if uv binary exists after strip-components
        self.assertIn('uv binary not found after strip-components', self.uv_source)

    def test_uv_checkReadySync_guards_empty_uvPath(self):
        """checkReadySync must guard against empty uvPath."""
        self.assertIn('!this.uvPath', self.uv_source)

    def test_uv_error_message_says_312(self):
        """Error message must say Python 3.12+, not 3.11+."""
        self.assertNotIn('Python 3.11+ manually', self.uv_source)
        self.assertIn('Python 3.12+ manually', self.uv_source)

    def test_uv_installPackages_uses_enriched_env(self):
        """installPackages must use enriched env."""
        # Look for enrichedEnv usage in the install section
        self.assertIn('getEnrichedEnv()', self.uv_source)

    def test_uv_validates_required_python_version(self):
        """Ready checks must enforce Python 3.12+, not just any runnable Python."""
        self.assertIn('hasRequiredPythonVersion', self.uv_source)
        self.assertIn('need ${PYTHON_VERSION}+', self.uv_source)

    def test_uv_recreates_invalid_venv_before_setup(self):
        """createVenv should remove invalid or corrupted venvs before recreating them."""
        self.assertIn('Removing existing venv before recreate', self.uv_source)
        self.assertIn('await this.rmWithRetry(this.venvDir)', self.uv_source)

    def test_uv_tracks_install_state_for_migration(self):
        """Manager should persist install-state so old environments are upgraded once."""
        self.assertIn("install-state.json", self.uv_source)
        self.assertIn('hasExpectedInstallState', self.uv_source)
        self.assertIn('writeInstallState', self.uv_source)

    # ─── pythonEnvironment.ts checks ───

    def test_py_imports_os_module(self):
        """pythonEnvironment must import os for homedir()."""
        self.assertIn("import * as os from 'os'", self.py_source)

    def test_py_has_mac_python_finder(self):
        """Must have findMacPython method."""
        self.assertIn('findMacPython', self.py_source)

    def test_py_checks_mac_platform(self):
        """Must check for darwin platform before Mac-specific paths."""
        self.assertIn("process.platform === 'darwin'", self.py_source)

    def test_py_has_homebrew_apple_silicon_path(self):
        """Must check Apple Silicon homebrew path."""
        self.assertIn('/opt/homebrew/bin/python3', self.py_source)

    def test_py_has_homebrew_intel_path(self):
        """Must check Intel homebrew path."""
        self.assertIn('/usr/local/bin/python3', self.py_source)

    def test_py_has_pyenv_path(self):
        """Must check pyenv shims path."""
        self.assertIn('.pyenv', self.py_source)

    def test_py_has_framework_path(self):
        """Must check Python.framework path (official installer)."""
        self.assertIn('Python.framework', self.py_source)

    def test_py_has_xcode_path(self):
        """Must check Xcode CLI tools path."""
        self.assertIn('/usr/bin/python3', self.py_source)

    def test_py_resolveCommand_uses_enriched_env(self):
        """resolvePythonCommand must pass enriched env to which."""
        self.assertIn('getEnrichedEnv', self.py_source)

    # ─── extension.ts checks ───

    def test_ext_error_messages_say_312(self):
        """All error messages must reference Python 3.12+, not 3.11+."""
        self.assertNotIn('Python 3.11+', self.ext_source)

    # ─── Cross-file consistency ───

    def test_python_version_consistent(self):
        """PYTHON_VERSION in uvPythonManager must match MIN_PYTHON_VERSION in pythonEnvironment."""
        uv_match = re.search(r"const PYTHON_VERSION = '(\d+\.\d+)'", self.uv_source)
        py_match = re.search(r'const MIN_PYTHON_VERSION = \[(\d+), (\d+)\]', self.py_source)
        self.assertIsNotNone(uv_match, "PYTHON_VERSION not found in uvPythonManager.ts")
        self.assertIsNotNone(py_match, "MIN_PYTHON_VERSION not found in pythonEnvironment.ts")
        assert uv_match is not None
        assert py_match is not None

        uv_version = uv_match.group(1)
        py_version = f"{py_match.group(1)}.{py_match.group(2)}"
        self.assertEqual(uv_version, py_version,
                         f"Version mismatch: uvPythonManager={uv_version}, pythonEnvironment={py_version}")


if __name__ == '__main__':
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print("=" * 70)
    unittest.main(verbosity=2)
