/**
 * UV Python Manager
 *
 * Uses uv (ultra-fast Python package manager) to manage Python environments.
 * uv is a single binary that can:
 * - Install Python versions automatically
 * - Create virtual environments
 * - Install packages 10-100x faster than pip
 *
 * This eliminates most Python installation issues for end users.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as https from 'https';
import type * as http from 'http';
import { execFile, execFileSync } from 'child_process';
import { createHash } from 'crypto';
import { promisify } from 'util';
import * as os from 'os';
import { PUBMED_SEARCH_PACKAGE, PUBMED_SEARCH_SOURCE_URL, PUBMED_SEARCH_VERSION } from './pubmedSearchPackage.js';
import { ZOTERO_KEEPER_PACKAGE, ZOTERO_KEEPER_SOURCE_URL, ZOTERO_KEEPER_VERSION } from './zoteroKeeperPackage.js';
import { buildAtomicPackageInstallArgs } from './uvCommands.js';

const execFileAsync = promisify(execFile);

// UV download URLs from GitHub releases. The version is pinned and every
// archive is verified against the SHA-256 published with that release
// (<archive>.sha256), so a truncated or tampered download never gets executed.
const UV_VERSION = '0.5.14';
const UV_RELEASE_BASE = `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}`;
interface UvDownload {
    url: string;
    executable: string;
    sha256: string;
}
const UV_DOWNLOADS: Record<string, UvDownload> = {
    // Windows
    'win32-x64': {
        url: `${UV_RELEASE_BASE}/uv-x86_64-pc-windows-msvc.zip`,
        executable: 'uv.exe',
        sha256: 'ee2468e40320a0a2a36435e66bbd0d861228c4c06767f22d97876528138f4ba0', // pragma: allowlist secret
    },
    'win32-ia32': {
        url: `${UV_RELEASE_BASE}/uv-i686-pc-windows-msvc.zip`,
        executable: 'uv.exe',
        sha256: '2ea709cf816b70661c6aa43d6aff7526faebafc2d45f7167d3192c5b9bb0a28f', // pragma: allowlist secret
    },
    // Linux
    'linux-x64': {
        url: `${UV_RELEASE_BASE}/uv-x86_64-unknown-linux-gnu.tar.gz`,
        executable: 'uv',
        sha256: '22034760075b92487b326da5aa1a2a3e1917e2e766c12c0fd466fccda77013c7', // pragma: allowlist secret
    },
    'linux-arm64': {
        url: `${UV_RELEASE_BASE}/uv-aarch64-unknown-linux-gnu.tar.gz`,
        executable: 'uv',
        sha256: '1c9cdb265b0c24ce2e74b7795a00842dc6d487c11ba49aa6c9ca1c784b82755a', // pragma: allowlist secret
    },
    // macOS
    'darwin-x64': {
        url: `${UV_RELEASE_BASE}/uv-x86_64-apple-darwin.tar.gz`,
        executable: 'uv',
        sha256: '8caf91b936ede1167abaebae07c2a1cbb22473355fa0ad7ebb2580307e84fb47', // pragma: allowlist secret
    },
    'darwin-arm64': {
        url: `${UV_RELEASE_BASE}/uv-aarch64-apple-darwin.tar.gz`,
        executable: 'uv',
        sha256: 'd548dffc256014c4c8c693e148140a3a21bcc2bf066a35e1d5f0d24c91d32112', // pragma: allowlist secret
    },
};

// Python version to install
// Python 3.12+ required for type parameter syntax (PEP 695), TaskGroup, etc.
const PYTHON_VERSION = '3.12';

// Required packages (pinned archives, see zoteroKeeperPackage.ts / pubmedSearchPackage.ts)
const REQUIRED_PACKAGES = [
    ZOTERO_KEEPER_PACKAGE,
    PUBMED_SEARCH_PACKAGE,
];

// Minimum versions for verification, keyed by import name
const MIN_VERSIONS: Record<string, string> = {
    'zotero_mcp': ZOTERO_KEEPER_VERSION,
    'pubmed_search': PUBMED_SEARCH_VERSION,
};

const SOURCE_URLS: Record<string, string> = {
    'zotero_mcp': ZOTERO_KEEPER_SOURCE_URL,
    'pubmed_search': PUBMED_SEARCH_SOURCE_URL,
};

// Timeout constants (in milliseconds)
const DOWNLOAD_TIMEOUT_MS = 60000;
const VENV_CREATION_TIMEOUT_MS = 300000;  // 5 minutes for Python download
const PACKAGE_INSTALL_TIMEOUT_MS = 300000;
const MAX_REDIRECTS = 5;

const REQUIRED_PYTHON_VERSION = PYTHON_VERSION.split('.').map(part => Number.parseInt(part, 10));
const INSTALL_STATE_FILE = 'install-state.json';

type InstallState = {
    pythonVersion: string;
    zoteroKeeperPackage: string;
    pubmedSearchPackage: string;
};

/** SHA-256 of a file, lowercase hex. */
export function sha256OfFile(filePath: string): string {
    return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

/** Throws unless the file's SHA-256 equals `expected` (case-insensitive hex). */
export function assertSha256(filePath: string, expected: string): void {
    const actual = sha256OfFile(filePath);
    if (actual !== expected.trim().toLowerCase()) {
        throw new Error(`Checksum mismatch for ${path.basename(filePath)}: expected ${expected}, got ${actual}`);
    }
}

/** Anchored pgrep pattern matching command lines that start with a path inside `dir` (POSIX). */
export function buildProcessPathPattern(dir: string): string {
    return `^${dir.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/`;
}

/** Positive integer PIDs from newline-separated tool output; everything else is dropped. */
export function parsePids(output: string): number[] {
    return output
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => /^\d+$/.test(line))
        .map(Number)
        .filter(pid => pid > 0);
}

type HttpsGet = (url: string, callback: (response: http.IncomingMessage) => void) => http.ClientRequest;

/**
 * Download over HTTPS only (redirects included) to `destPath`. On any failure
 * (non-200, truncated body, timeout, redirect to plain HTTP) the partial file
 * is removed and the promise rejects; it never hangs on a dropped connection.
 */
export function downloadFile(
    url: string,
    destPath: string,
    onProgress?: (percent: number) => void,
    get: HttpsGet = https.get,
): Promise<void> {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(destPath);
        let settled = false;

        const fail = (error: Error): void => {
            if (settled) { return; }
            settled = true;
            file.destroy();
            fs.rm(destPath, { force: true }, () => reject(error));
        };

        const request = (requestUrl: string, redirects: number): void => {
            if (redirects > MAX_REDIRECTS) {
                fail(new Error('Too many redirects'));
                return;
            }
            let target: URL;
            try {
                target = new URL(requestUrl);
            } catch {
                fail(new Error(`Invalid download URL: ${requestUrl}`));
                return;
            }
            if (target.protocol !== 'https:') {
                fail(new Error(`Refusing non-HTTPS download: ${requestUrl}`));
                return;
            }

            const clientRequest = get(target.toString(), (response) => {
                const status = response.statusCode ?? 0;
                if ([301, 302, 303, 307, 308].includes(status)) {
                    response.resume();
                    const location = response.headers.location;
                    if (!location) {
                        fail(new Error(`Redirect (HTTP ${status}) without a Location header`));
                        return;
                    }
                    request(new URL(location, target).toString(), redirects + 1);
                    return;
                }
                if (status !== 200) {
                    response.resume();
                    fail(new Error(`Download failed: HTTP ${status}`));
                    return;
                }

                const totalSize = Number.parseInt(String(response.headers['content-length'] ?? '0'), 10) || 0;
                let downloadedSize = 0;
                let lastPercent = 0;
                response.on('data', (chunk: Buffer) => {
                    downloadedSize += chunk.length;
                    if (totalSize > 0 && onProgress) {
                        const percent = Math.round((downloadedSize / totalSize) * 100);
                        if (percent !== lastPercent) {
                            lastPercent = percent;
                            onProgress(percent);
                        }
                    }
                });
                response.on('error', fail);
                response.on('close', () => {
                    if (!response.complete) { fail(new Error('Download interrupted')); }
                });
                response.pipe(file);
            });

            clientRequest.on('error', fail);
            clientRequest.setTimeout(DOWNLOAD_TIMEOUT_MS, () => {
                clientRequest.destroy();
                fail(new Error('Download timeout'));
            });
        };

        file.on('error', fail);
        file.on('close', () => {
            if (!settled) {
                settled = true;
                resolve();
            }
        });
        request(url, 0);
    });
}

/**
 * Build enriched PATH for macOS.
 * VS Code launched from Finder/Dock does NOT inherit shell PATH,
 * so common locations like /opt/homebrew/bin are missing.
 */
function getEnrichedEnv(): NodeJS.ProcessEnv {
    if (process.platform !== 'darwin') {
        return process.env;
    }
    const home = os.homedir();
    const extraPaths = [
        '/opt/homebrew/bin',           // Apple Silicon homebrew
        '/opt/homebrew/sbin',
        '/usr/local/bin',              // Intel homebrew / manual installs
        '/usr/local/sbin',
        path.join(home, '.local', 'bin'),  // pipx, uv, cargo installs
        path.join(home, '.cargo', 'bin'),  // cargo (uv may be here)
        path.join(home, '.pyenv', 'shims'), // pyenv
    ].filter(p => fs.existsSync(p));

    if (extraPaths.length === 0) {
        return process.env;
    }

    return {
        ...process.env,
        PATH: [...extraPaths, process.env.PATH || ''].join(':'),
    };
}

export class UvPythonManager implements vscode.Disposable {
    private outputChannel: vscode.OutputChannel;
    private baseDir: string;
    private uvPath: string;
    private venvDir: string;
    private pythonBinary: string;
    private installStatePath: string;
    private _isReady: boolean = false;
    private _ensurePromise: Promise<string> | undefined;

    constructor(context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('Zotero MCP Setup');

        // Setup paths
        this.baseDir = context.globalStorageUri.fsPath;
        this.uvPath = this.getUvPath();
        this.venvDir = path.join(this.baseDir, 'venv');
        this.pythonBinary = this.getPythonBinaryPath();
        this.installStatePath = path.join(this.baseDir, INSTALL_STATE_FILE);

        // Check if already ready
        this._isReady = this.checkReadySync();
    }

    private getPlatformKey(): string {
        return `${process.platform}-${process.arch}`;
    }

    private getUvPath(): string {
        const platformKey = this.getPlatformKey();
        const info = UV_DOWNLOADS[platformKey];
        if (!info) {
            return '';
        }
        return path.join(this.baseDir, 'uv', info.executable);
    }

    private getPythonBinaryPath(): string {
        if (process.platform === 'win32') {
            return path.join(this.venvDir, 'Scripts', 'python.exe');
        }
        return path.join(this.venvDir, 'bin', 'python');
    }

    private getExpectedInstallState(): InstallState {
        return {
            pythonVersion: PYTHON_VERSION,
            zoteroKeeperPackage: ZOTERO_KEEPER_PACKAGE,
            pubmedSearchPackage: PUBMED_SEARCH_PACKAGE,
        };
    }

    private readInstallStateSync(): InstallState | null {
        if (!fs.existsSync(this.installStatePath)) {
            return null;
        }

        try {
            const raw = fs.readFileSync(this.installStatePath, 'utf-8');
            return JSON.parse(raw) as InstallState;
        } catch {
            return null;
        }
    }

    private hasExpectedInstallState(): boolean {
        const actual = this.readInstallStateSync();
        if (!actual) {
            return false;
        }

        const expected = this.getExpectedInstallState();
        return actual.pythonVersion === expected.pythonVersion
            && actual.zoteroKeeperPackage === expected.zoteroKeeperPackage
            && actual.pubmedSearchPackage === expected.pubmedSearchPackage;
    }

    private writeInstallState(): void {
        fs.writeFileSync(this.installStatePath, JSON.stringify(this.getExpectedInstallState(), null, 2), 'utf-8');
    }

    private hasRequiredPythonVersion(versionOutput: string): boolean {
        const match = versionOutput.match(/Python\s+(\d+)\.(\d+)/);
        if (!match) {
            return false;
        }

        const major = Number.parseInt(match[1], 10);
        const minor = Number.parseInt(match[2], 10);
        const [requiredMajor, requiredMinor] = REQUIRED_PYTHON_VERSION;

        return major > requiredMajor || (major === requiredMajor && minor >= requiredMinor);
    }

    private getPythonVersionOutputSync(pythonPath: string): string | null {
        try {
            return execFileSync(
                pythonPath,
                ['--version'],
                { encoding: 'utf-8', stdio: 'pipe', timeout: 10000, env: getEnrichedEnv(), windowsHide: true }
            ).trim();
        } catch {
            return null;
        }
    }

    private checkReadySync(): boolean {
        if (!this.uvPath || !fs.existsSync(this.pythonBinary) || !fs.existsSync(this.uvPath)) {
            return false;
        }
        const output = this.getPythonVersionOutputSync(this.pythonBinary);
        if (!output) {
            return false;
        }

        return this.hasRequiredPythonVersion(output) && this.hasExpectedInstallState();
    }

    isReady(): boolean {
        return this._isReady;
    }

    getPythonPath(): string {
        return this.pythonBinary;
    }

    async getPythonVersion(): Promise<string | undefined> {
        if (!this._isReady) {
            return undefined;
        }
        const output = this.getPythonVersionOutputSync(this.pythonBinary);
        return output ? output.replace('Python ', '') : undefined;
    }

    /**
     * Verify Python and packages are ready (with version check)
     */
    async verifyReady(): Promise<boolean> {
        if (!fs.existsSync(this.pythonBinary)) {
            this._isReady = false;
            return false;
        }

        try {
            // Verify Python binary is actually runnable (not corrupted)
            const pythonVersionOutput = this.getPythonVersionOutputSync(this.pythonBinary);

            // Verify it's actually a Python process that responds properly
            if (!pythonVersionOutput) {
                this.log('Python binary exists but returned no version output');
                this._isReady = false;
                return false;
            }

            if (!this.hasRequiredPythonVersion(pythonVersionOutput)) {
                this.log(`Python ${pythonVersionOutput} is too old, need ${PYTHON_VERSION}+`);
                this._isReady = false;
                return false;
            }

            if (!this.hasExpectedInstallState()) {
                this.log('Install state missing or outdated, package refresh required');
                this._isReady = false;
                return false;
            }

            // Check if packages are installed AND meet minimum version requirements
            // Write script to temp file to avoid shell escaping issues
            const scriptPath = path.join(this.baseDir, 'version_check.py');
            // IMPORTANT: Use importlib.metadata.version() instead of __version__ attribute
            // because some packages have __version__ mismatches with their installed version.
            // importlib.metadata reads the actual installed package metadata from dist-info
            const versionCheckScript = `
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

# Use importlib.metadata for accurate version detection
# __version__ attributes can be stale/incorrect (known issue with some packages)
from importlib.metadata import version as get_version, PackageNotFoundError, distribution

# Map from module name to PyPI package name for metadata lookup
_pkg_names = {
    'zotero_mcp': 'zotero-keeper',
    'pubmed_search': 'pubmed-search-mcp',
}

min_versions = ${JSON.stringify(MIN_VERSIONS)}
source_urls = ${JSON.stringify(SOURCE_URLS)}
for mod_name, min_ver in min_versions.items():
    try:
        pkg_name = _pkg_names.get(mod_name, mod_name)
        actual_ver = get_version(pkg_name)
    except PackageNotFoundError:
        print(f"MISSING:Package metadata not found for {mod_name}")
        sys.exit(0)
    if Version(actual_ver) < Version(min_ver):
        print(f"OUTDATED:{mod_name}:{actual_ver}:<{min_ver}")
        sys.exit(0)
    expected_source = source_urls.get(mod_name)
    if expected_source:
        direct_url = distribution(pkg_name).read_text("direct_url.json") or ""
        if expected_source not in direct_url:
            print(f"OUTDATED_SOURCE:{mod_name}")
            sys.exit(0)
print("OK")
`;
            fs.writeFileSync(scriptPath, versionCheckScript, 'utf-8');

            try {
                const { stdout } = await execFileAsync(
                    this.pythonBinary,
                    [scriptPath],
                    { encoding: 'utf-8', timeout: 60000, windowsHide: true }
                );

                const output = stdout.trim();
                if (output === 'OK') {
                    this._isReady = true;
                    return true;
                }

                this.log(`Version check result: ${output}`);
                this._isReady = false;
                return false;
            } finally {
                // Clean up temp script - ignore errors as file may not exist
                try { fs.unlinkSync(scriptPath); } catch { /* intentionally empty */ }
            }
        } catch (error) {
            this.log(`verifyReady failed: ${error}`);
            this._isReady = false;
            return false;
        }
    }

    /**
     * Check if Python binary exists and works, but packages might need upgrade.
     * This does a quick validation to avoid trying upgrades on corrupted environments.
     */
    private needsUpgradeOnly(): boolean {
        if (!fs.existsSync(this.pythonBinary) || !fs.existsSync(this.uvPath)) {
            return false;
        }
        const output = this.getPythonVersionOutputSync(this.pythonBinary);
        if (!output) {
            this.log('Python binary exists but is not runnable, needs full rebuild');
            return false;
        }

        if (!this.hasRequiredPythonVersion(output)) {
            this.log(`Python ${output} does not satisfy ${PYTHON_VERSION}+, needs full rebuild`);
            return false;
        }

        return true;
    }

    /**
     * Main entry point - ensure everything is ready.
     * Concurrent callers (activation + setup wizard, for example) share one run.
     */
    ensureReady(): Promise<string> {
        if (!this._ensurePromise) {
            this._ensurePromise = this.runEnsureReady().finally(() => {
                this._ensurePromise = undefined;
            });
        }
        return this._ensurePromise;
    }

    private async runEnsureReady(): Promise<string> {
        // Check if already set up with correct versions
        if (await this.verifyReady()) {
            this.log('Python environment is already ready');
            return this.pythonBinary;
        }

        // Check if we just need to upgrade packages (not full setup)
        if (this.needsUpgradeOnly()) {
            this.log('Python exists but packages need upgrade...');

            const upgraded = await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: 'Upgrading MCP packages',
                    cancellable: false
                },
                async (progress) => {
                    progress.report({ message: 'Checking package versions...' });
                    const success = await this.upgradePackages();
                    if (success) {
                        progress.report({ message: 'Upgrade complete!' });
                    }
                    return success;
                }
            );

            if (upgraded && await this.verifyReady()) {
                this.log('Package upgrade successful');
                return this.pythonBinary;
            }

            this.log('Package upgrade failed, will try full setup');
        }

        return vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Setting up Python environment',
                cancellable: false
            },
            async (progress) => {
                const success = await this.setup(progress);
                if (success) {
                    this._isReady = true;
                    return this.pythonBinary;
                }
                throw new Error('Failed to set up Python environment');
            }
        );
    }

    /**
     * Full setup process
     */
    async setup(progress: vscode.Progress<{ message?: string; increment?: number }>): Promise<boolean> {
        const platformKey = this.getPlatformKey();
        const uvInfo = UV_DOWNLOADS[platformKey];

        if (!uvInfo) {
            vscode.window.showErrorMessage(
                `Unsupported platform: ${platformKey}. Please install Python 3.12+ manually.`
            );
            return false;
        }

        try {
            // Create directories
            fs.mkdirSync(this.baseDir, { recursive: true });

            // Step 1: Download and extract uv
            if (!fs.existsSync(this.uvPath)) {
                progress.report({ message: 'Downloading uv package manager (~10MB)...', increment: 0 });
                this.log(`Downloading uv for ${platformKey}...`);
                await this.downloadAndExtractUv(uvInfo, progress);
            } else {
                this.log('uv already exists');
            }

            // Step 2: Create venv with Python
            progress.report({ message: 'Creating Python environment...', increment: 30 });
            this.log('Creating virtual environment with Python...');
            await this.createVenv();

            // Step 3: Install packages
            progress.report({ message: 'Installing MCP packages...', increment: 50 });
            this.log('Installing packages...');
            await this.installPackages((msg) => {
                progress.report({ message: msg });
            });

            progress.report({ message: 'Setup complete!', increment: 100 });
            this.log('Setup complete!');

            return true;

        } catch (error) {
            this.log(`Setup failed: ${error}`);
            this.showOutput();
            vscode.window.showErrorMessage(`Failed to setup Python environment: ${error}`);
            return false;
        }
    }

    /**
     * Download and extract uv
     */
    private async downloadAndExtractUv(
        download: UvDownload,
        progress: vscode.Progress<{ message?: string; increment?: number }>
    ): Promise<void> {
        const uvDir = path.join(this.baseDir, 'uv');
        fs.mkdirSync(uvDir, { recursive: true });

        const isZip = download.url.endsWith('.zip');
        const archivePath = path.join(uvDir, isZip ? 'uv.zip' : 'uv.tar.gz');

        try {
            await downloadFile(download.url, archivePath, (percent) => {
                progress.report({ message: `Downloading uv... ${percent}%` });
            });
            // Never extract (let alone execute) an archive that is not the pinned release.
            assertSha256(archivePath, download.sha256);

            this.log(`Extracting uv to ${uvDir}...`);
            if (isZip) {
                // Windows: PowerShell extracts zip; the path is passed as a single-quoted literal.
                const literal = (value: string): string => `'${value.replace(/'/g, "''")}'`;
                await execFileAsync(
                    'powershell',
                    [
                        '-NoProfile',
                        '-NonInteractive',
                        '-Command',
                        `Expand-Archive -LiteralPath ${literal(archivePath)} -DestinationPath ${literal(uvDir)} -Force`,
                    ],
                    { encoding: 'utf-8', windowsHide: true, timeout: 120000 }
                );
            } else {
                // Unix: first try --strip-components=1 (standard for uv releases)
                await execFileAsync(
                    'tar',
                    ['-xzf', archivePath, '-C', uvDir, '--strip-components=1'],
                    { encoding: 'utf-8', timeout: 120000 }
                );

                // Some tar versions or archive structures may put files differently
                if (!fs.existsSync(this.uvPath)) {
                    this.log('uv binary not found after strip-components=1, searching...');
                    const found = this.findFileRecursive(uvDir, 'uv');
                    if (!found) {
                        throw new Error('uv binary not found after extraction');
                    }
                    this.log(`Found uv at ${found}, copying to ${this.uvPath}`);
                    fs.copyFileSync(found, this.uvPath);
                }
            }
        } finally {
            fs.rmSync(archivePath, { force: true });
        }

        // Make executable on Unix
        if (process.platform !== 'win32') {
            fs.chmodSync(this.uvPath, 0o755);
        }

        // Final verification
        if (!fs.existsSync(this.uvPath)) {
            throw new Error(`uv binary not found at expected path: ${this.uvPath}`);
        }

        this.log('uv extracted successfully');
    }

    /**
     * Create virtual environment with Python
     */
    private async createVenv(): Promise<void> {
        if (fs.existsSync(this.venvDir)) {
            const versionOutput = this.getPythonVersionOutputSync(this.pythonBinary);
            const shouldRecreate = !versionOutput || !this.hasRequiredPythonVersion(versionOutput);

            if (shouldRecreate) {
                const reason = versionOutput
                    ? `found ${versionOutput}, need ${PYTHON_VERSION}+`
                    : 'existing environment is incomplete or corrupted';
                this.log(`Removing existing venv before recreate: ${reason}`);
                await this.killPythonProcesses();
                await this.rmWithRetry(this.venvDir);
            }
        }

        // uv can automatically download and install Python!
        this.log(`Running: ${this.uvPath} venv ${this.venvDir} --python ${PYTHON_VERSION}`);

        try {
            const enrichedEnv = getEnrichedEnv();
            await execFileAsync(this.uvPath, ['venv', this.venvDir, '--python', PYTHON_VERSION], {
                encoding: 'utf-8',
                timeout: VENV_CREATION_TIMEOUT_MS,
                windowsHide: true,
                env: {
                    ...enrichedEnv,
                    // Allow uv to download Python
                    UV_PYTHON_DOWNLOADS: 'automatic',
                    // Ensure HOME is set (macOS GUI apps may not have it)
                    HOME: enrichedEnv.HOME || os.homedir(),
                }
            });
            this.log('Virtual environment created');
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.log(`venv creation error: ${errorMessage}`);
            throw error;
        }
    }

    /**
     * Install packages using uv (much faster than pip!)
     * Uses --upgrade to ensure packages meet minimum version requirements
     */
    private async installPackages(onProgress?: (msg: string) => void): Promise<void> {
        const enrichedEnv = getEnrichedEnv();
        const baseEnv = { ...enrichedEnv, VIRTUAL_ENV: this.venvDir };

        // First, install packaging for version checks
        try {
            await execFileAsync(
                this.uvPath,
                ['pip', 'install', '--python', this.pythonBinary, 'packaging'],
                { encoding: 'utf-8', timeout: DOWNLOAD_TIMEOUT_MS, windowsHide: true, env: baseEnv }
            );
        } catch {
            // packaging may already be installed - safe to continue
            this.log('packaging already installed or install skipped');
        }

        // Resolve and replace the mutually compatible Keeper, PubMed Search,
        // and MCP SDK versions together. Installing one package at a time can
        // temporarily leave a running environment with incompatible SDK majors.
        const packageNames = REQUIRED_PACKAGES
            .map(pkg => pkg.split(' ', 1)[0].split('>=', 1)[0].split('[', 1)[0])
            .join(' + ');
        this.log(`Installing/upgrading together: ${REQUIRED_PACKAGES.join(', ')}`);
        onProgress?.(`Installing ${packageNames}...`);

        try {
            await execFileAsync(
                this.uvPath,
                buildAtomicPackageInstallArgs(this.pythonBinary, REQUIRED_PACKAGES),
                {
                    encoding: 'utf-8',
                    timeout: PACKAGE_INSTALL_TIMEOUT_MS,
                    windowsHide: true,
                    maxBuffer: 10 * 1024 * 1024,
                    env: baseEnv,
                }
            );
        } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.log(`Error installing required package set: ${errorMessage}`);
            throw error;
        }

        this.writeInstallState();

        this.log('All packages installed successfully');
    }

    /**
     * Upgrade packages to meet current version requirements
     * Called when verifyReady() detects outdated packages
     */
    async upgradePackages(): Promise<boolean> {
        if (!fs.existsSync(this.uvPath) || !fs.existsSync(this.pythonBinary)) {
            return false;
        }

        this.log('Upgrading packages to meet version requirements...');

        try {
            // Old VSIX installs may leave MCP server processes running from this
            // venv. Stop them before replacing packages on Windows.
            await this.killPythonProcesses();
            await this.installPackages((msg) => {
                this.log(msg);
            });
            return true;
        } catch (error) {
            this.log(`Package upgrade failed: ${error}`);
            this.showOutput();  // Only show output on failure
            return false;
        }
    }

    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
        console.log(`[UvPython] ${message}`);
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    dispose(): void {
        this.outputChannel.dispose();
    }

    /**
     * Recursively search for a file by name within a directory.
     * Used as fallback when tar extraction puts files in unexpected locations.
     */
    private findFileRecursive(dir: string, filename: string): string | null {
        try {
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isFile() && entry.name === filename) {
                    return fullPath;
                }
                if (entry.isDirectory()) {
                    const found = this.findFileRecursive(fullPath, filename);
                    if (found) {
                        return found;
                    }
                }
            }
        } catch {
            // directory may not be readable
        }
        return null;
    }

    /**
     * Kill any running processes that use the venv Python binary.
     * This is required on Windows where running .exe files cannot be deleted (EPERM).
     * MCP servers spawn python.exe processes that hold file locks.
     * Only processes whose executable lives inside this venv are matched; the
     * venv path is passed through the environment/anchored pattern, never
     * spliced into a shell command.
     */
    private async killPythonProcesses(): Promise<void> {
        if (!fs.existsSync(this.pythonBinary)) {
            return;
        }

        try {
            let pids: number[] = [];
            if (process.platform === 'win32') {
                const { stdout } = await execFileAsync(
                    'powershell',
                    [
                        '-NoProfile',
                        '-NonInteractive',
                        '-Command',
                        'Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($env:ZK_VENV_DIR, [StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { $_.ProcessId }',
                    ],
                    {
                        encoding: 'utf-8',
                        timeout: 20000,
                        windowsHide: true,
                        env: { ...process.env, ZK_VENV_DIR: this.venvDir + path.sep },
                    }
                );
                pids = parsePids(stdout);
            } else {
                try {
                    const { stdout } = await execFileAsync(
                        'pgrep',
                        ['-f', buildProcessPathPattern(this.venvDir)],
                        { encoding: 'utf-8', timeout: 5000 }
                    );
                    pids = parsePids(stdout);
                } catch {
                    // pgrep exits 1 when nothing matches
                }
            }

            pids = pids.filter(pid => pid !== process.pid);
            for (const pid of pids) {
                this.log(`Killing process PID ${pid} using venv Python...`);
                try {
                    process.kill(pid, 'SIGKILL');
                } catch {
                    // Process may have already exited
                }
            }
            if (pids.length > 0) {
                // Wait for the OS to release file handles
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        } catch (error) {
            this.log(`Warning: Could not kill Python processes: ${error}`);
            // Continue with cleanup anyway - rmSync with force may still work
        }
    }

    /**
     * Remove a directory with retry logic for Windows file locking.
     * Even after killing processes, Windows may take a moment to release file handles.
     */
    private async rmWithRetry(dirPath: string, maxRetries = 3): Promise<void> {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                fs.rmSync(dirPath, { recursive: true, force: true });
                return; // Success
            } catch (error: unknown) {
                const errCode = error instanceof Error && 'code' in error ? error.code : undefined;
                if ((errCode === 'EPERM' || errCode === 'EBUSY') && attempt < maxRetries) {
                    this.log(`Retry ${attempt}/${maxRetries}: File locked, waiting before retry...`);
                    await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
                } else {
                    throw error;
                }
            }
        }
    }

    /**
     * Clean up for reinstall
     */
    async cleanup(): Promise<void> {
        this.log('Cleaning up Python environment...');

        // Step 1: Kill any running processes using our venv Python
        // This prevents EPERM errors on Windows when python.exe is locked
        await this.killPythonProcesses();

        // Step 2: Remove venv with retry (Windows may need extra time to release handles)
        if (fs.existsSync(this.venvDir)) {
            await this.rmWithRetry(this.venvDir);
        }

        // Step 3: Remove uv too
        const uvDir = path.join(this.baseDir, 'uv');
        if (fs.existsSync(uvDir)) {
            await this.rmWithRetry(uvDir);
        }

        if (fs.existsSync(this.installStatePath)) {
            fs.rmSync(this.installStatePath, { force: true });
        }

        this._isReady = false;
        this.log('Cleanup complete');
    }
}
