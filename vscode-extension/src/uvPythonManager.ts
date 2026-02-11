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
import * as http from 'http';
import { execSync } from 'child_process';

// UV download URLs from GitHub releases
// Using latest stable version
const UV_VERSION = '0.5.14';
const UV_DOWNLOADS: Record<string, { url: string; executable: string }> = {
    // Windows
    'win32-x64': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-pc-windows-msvc.zip`,
        executable: 'uv.exe'
    },
    'win32-ia32': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-i686-pc-windows-msvc.zip`,
        executable: 'uv.exe'
    },
    // Linux
    'linux-x64': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz`,
        executable: 'uv'
    },
    'linux-arm64': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-aarch64-unknown-linux-gnu.tar.gz`,
        executable: 'uv'
    },
    // macOS
    'darwin-x64': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-apple-darwin.tar.gz`,
        executable: 'uv'
    },
    'darwin-arm64': {
        url: `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-aarch64-apple-darwin.tar.gz`,
        executable: 'uv'
    },
};

// Python version to install
// Python 3.12+ required for type parameter syntax (PEP 695), TaskGroup, etc.
const PYTHON_VERSION = '3.12';

// Required packages with minimum versions
// IMPORTANT: Update these when extension depends on new package features
// Python 3.12+ required for new core module features
const REQUIRED_PACKAGES = [
    'zotero-keeper>=1.11.0',
    'pubmed-search-mcp>=0.3.8',
];

// Minimum versions for verification (extracted from REQUIRED_PACKAGES)
// IMPORTANT: Keep in sync with REQUIRED_PACKAGES above!
const MIN_VERSIONS: Record<string, string> = {
    'zotero_mcp': '1.11.0',
    'pubmed_search': '0.3.8',
};

// Timeout constants (in milliseconds)
const SETUP_POLL_INTERVAL_MS = 1000;
const DOWNLOAD_TIMEOUT_MS = 60000;
const VENV_CREATION_TIMEOUT_MS = 300000;  // 5 minutes for Python download
const PACKAGE_INSTALL_TIMEOUT_MS = 300000;

export class UvPythonManager {
    private context: vscode.ExtensionContext;
    private outputChannel: vscode.OutputChannel;
    private baseDir: string;
    private uvPath: string;
    private venvDir: string;
    private pythonBinary: string;
    private _isReady: boolean = false;
    private _setupInProgress: boolean = false;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.outputChannel = vscode.window.createOutputChannel('Zotero MCP Setup');

        // Setup paths
        this.baseDir = context.globalStorageUri.fsPath;
        this.uvPath = this.getUvPath();
        this.venvDir = path.join(this.baseDir, 'venv');
        this.pythonBinary = this.getPythonBinaryPath();

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

    private checkReadySync(): boolean {
        if (!fs.existsSync(this.pythonBinary) || !fs.existsSync(this.uvPath)) {
            return false;
        }
        // Quick validation: ensure Python binary is runnable (not corrupted)
        try {
            const output = execSync(
                `"${this.pythonBinary}" --version`,
                { encoding: 'utf-8', stdio: 'pipe', timeout: 10000 }
            );
            return output.trim().startsWith('Python');
        } catch {
            return false;
        }
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
        try {
            const output = execSync(`"${this.pythonBinary}" --version`, {
                encoding: 'utf-8',
                stdio: 'pipe'
            });
            return output.trim().replace('Python ', '');
        } catch {
            // Python binary may not exist or be executable
            return undefined;
        }
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
            const pythonVersionOutput = execSync(
                `"${this.pythonBinary}" --version`,
                { encoding: 'utf-8', stdio: 'pipe', timeout: 10000 }
            );

            // Verify it's actually a Python process that responds properly
            if (!pythonVersionOutput.trim().startsWith('Python')) {
                this.log(`Python binary exists but returned unexpected output: ${pythonVersionOutput.trim()}`);
                this._isReady = false;
                return false;
            }

            // Check if packages are installed AND meet minimum version requirements
            // Write script to temp file to avoid shell escaping issues
            const scriptPath = path.join(this.baseDir, 'version_check.py');
            // IMPORTANT: Use importlib.metadata.version() instead of __version__ attribute
            // because some packages have __version__ mismatches with their installed version
            // (e.g., pubmed-search-mcp 0.3.8 reports __version__="0.3.6")
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
from importlib.metadata import version as get_version, PackageNotFoundError

# Map from module name to PyPI package name for metadata lookup
_pkg_names = {
    'zotero_mcp': 'zotero-keeper',
    'pubmed_search': 'pubmed-search-mcp',
}

min_versions = ${JSON.stringify(MIN_VERSIONS)}
for mod_name, min_ver in min_versions.items():
    try:
        actual_ver = get_version(_pkg_names.get(mod_name, mod_name))
    except PackageNotFoundError:
        print(f"MISSING:Package metadata not found for {mod_name}")
        sys.exit(0)
    if Version(actual_ver) < Version(min_ver):
        print(f"OUTDATED:{mod_name}:{actual_ver}:<{min_ver}")
        sys.exit(0)
print("OK")
`;
            fs.writeFileSync(scriptPath, versionCheckScript, 'utf-8');

            try {
                const result = execSync(
                    `"${this.pythonBinary}" "${scriptPath}"`,
                    { encoding: 'utf-8', stdio: 'pipe' }
                );

                const output = result.trim();
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
        // Verify Python binary is actually runnable
        try {
            const output = execSync(
                `"${this.pythonBinary}" --version`,
                { encoding: 'utf-8', stdio: 'pipe', timeout: 10000 }
            );
            return output.trim().startsWith('Python');
        } catch {
            this.log('Python binary exists but is not runnable, needs full rebuild');
            return false;
        }
    }

    /**
     * Main entry point - ensure everything is ready
     */
    async ensureReady(): Promise<string> {
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

        // Prevent concurrent setup
        if (this._setupInProgress) {
            this.log('Setup already in progress, waiting...');
            while (this._setupInProgress) {
                await new Promise(resolve => setTimeout(resolve, SETUP_POLL_INTERVAL_MS));
            }
            if (this._isReady) {
                return this.pythonBinary;
            }
            throw new Error('Concurrent setup failed');
        }

        this._setupInProgress = true;

        try {
            return await vscode.window.withProgress(
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
        } finally {
            this._setupInProgress = false;
        }
    }

    /**
     * Full setup process
     */
    async setup(progress: vscode.Progress<{ message?: string; increment?: number }>): Promise<boolean> {
        const platformKey = this.getPlatformKey();
        const uvInfo = UV_DOWNLOADS[platformKey];

        if (!uvInfo) {
            vscode.window.showErrorMessage(
                `Unsupported platform: ${platformKey}. Please install Python 3.11+ manually.`
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
                await this.downloadAndExtractUv(uvInfo.url, progress);
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
        url: string,
        progress: vscode.Progress<{ message?: string; increment?: number }>
    ): Promise<void> {
        const uvDir = path.join(this.baseDir, 'uv');
        fs.mkdirSync(uvDir, { recursive: true });

        const isZip = url.endsWith('.zip');
        const archivePath = path.join(uvDir, isZip ? 'uv.zip' : 'uv.tar.gz');

        // Download
        await this.downloadFile(url, archivePath, (percent) => {
            progress.report({ message: `Downloading uv... ${percent}%` });
        });

        // Extract
        this.log(`Extracting uv to ${uvDir}...`);

        if (isZip) {
            // Windows: use PowerShell to extract zip
            execSync(
                `powershell -Command "Expand-Archive -Path '${archivePath}' -DestinationPath '${uvDir}' -Force"`,
                { encoding: 'utf-8', stdio: 'pipe' }
            );
        } else {
            // Unix: use tar
            execSync(`tar -xzf "${archivePath}" -C "${uvDir}" --strip-components=1`, {
                encoding: 'utf-8',
                stdio: 'pipe'
            });
        }

        // Clean up archive
        fs.unlinkSync(archivePath);

        // Make executable on Unix
        if (process.platform !== 'win32') {
            fs.chmodSync(this.uvPath, 0o755);
        }

        this.log('uv extracted successfully');
    }

    /**
     * Create virtual environment with Python
     */
    private async createVenv(): Promise<void> {
        // uv can automatically download and install Python!
        const cmd = `"${this.uvPath}" venv "${this.venvDir}" --python ${PYTHON_VERSION}`;
        this.log(`Running: ${cmd}`);

        try {
            execSync(cmd, {
                encoding: 'utf-8',
                stdio: 'pipe',
                timeout: VENV_CREATION_TIMEOUT_MS,
                env: {
                    ...process.env,
                    // Allow uv to download Python
                    UV_PYTHON_DOWNLOADS: 'automatic',
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
        // First, install packaging for version checks
        try {
            const packagingCmd = `"${this.uvPath}" pip install --python "${this.pythonBinary}" packaging`;
            execSync(packagingCmd, {
                encoding: 'utf-8',
                stdio: 'pipe',
                timeout: DOWNLOAD_TIMEOUT_MS,
                env: { ...process.env, VIRTUAL_ENV: this.venvDir }
            });
        } catch {
            // packaging may already be installed - safe to continue
            this.log('packaging already installed or install skipped');
        }

        for (const pkg of REQUIRED_PACKAGES) {
            const pkgName = pkg.split('>=')[0].split('[')[0];
            this.log(`Installing/upgrading: ${pkg}`);
            onProgress?.(`Installing ${pkgName}...`);

            // Use --upgrade to ensure version requirements are met
            const cmd = `"${this.uvPath}" pip install --upgrade --python "${this.pythonBinary}" "${pkg}"`;

            try {
                execSync(cmd, {
                    encoding: 'utf-8',
                    stdio: 'pipe',
                    timeout: PACKAGE_INSTALL_TIMEOUT_MS,
                    env: {
                        ...process.env,
                        VIRTUAL_ENV: this.venvDir,
                    }
                });
            } catch (error: unknown) {
                const errorMessage = error instanceof Error ? error.message : String(error);
                this.log(`Error installing ${pkg}: ${errorMessage}`);
                throw error;
            }
        }

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

    /**
     * Download file with progress
     */
    private async downloadFile(
        url: string,
        destPath: string,
        onProgress?: (percent: number) => void
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            const file = fs.createWriteStream(destPath);

            const doRequest = (requestUrl: string, redirectCount = 0) => {
                if (redirectCount > 5) {
                    reject(new Error('Too many redirects'));
                    return;
                }

                const protocol = requestUrl.startsWith('https') ? https : http;

                const request = protocol.get(requestUrl, (response) => {
                    if (response.statusCode === 301 || response.statusCode === 302 || response.statusCode === 307) {
                        const redirectUrl = response.headers.location;
                        if (redirectUrl) {
                            this.log(`Redirecting to: ${redirectUrl}`);
                            doRequest(redirectUrl, redirectCount + 1);
                            return;
                        }
                    }

                    if (response.statusCode !== 200) {
                        reject(new Error(`Download failed: HTTP ${response.statusCode}`));
                        return;
                    }

                    const totalSize = parseInt(response.headers['content-length'] || '0', 10);
                    let downloadedSize = 0;
                    let lastPercent = 0;

                    response.on('data', (chunk) => {
                        downloadedSize += chunk.length;
                        if (totalSize > 0 && onProgress) {
                            const percent = Math.round((downloadedSize / totalSize) * 100);
                            if (percent !== lastPercent) {
                                lastPercent = percent;
                                onProgress(percent);
                            }
                        }
                    });

                    response.pipe(file);

                    file.on('finish', () => {
                        file.close();
                        this.log(`Download complete: ${destPath}`);
                        resolve();
                    });
                });

                request.on('error', (err) => {
                    fs.unlink(destPath, () => {});
                    reject(err);
                });

                request.setTimeout(DOWNLOAD_TIMEOUT_MS, () => {
                    request.destroy();
                    reject(new Error('Download timeout'));
                });
            };

            doRequest(url);
        });
    }

    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
        console.log(`[UvPython] ${message}`);
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    /**
     * Kill any running processes that use the venv Python binary.
     * This is required on Windows where running .exe files cannot be deleted (EPERM).
     * MCP servers spawn python.exe processes that hold file locks.
     */
    private async killPythonProcesses(): Promise<void> {
        if (!fs.existsSync(this.pythonBinary)) {
            return;
        }

        try {
            if (process.platform === 'win32') {
                // Find and kill processes using our specific python.exe
                // Use WMIC to find PIDs matching our venv path
                const venvScriptsDir = path.join(this.venvDir, 'Scripts').replace(/\\/g, '\\\\');
                try {
                    const wmicOutput = execSync(
                        `wmic process where "ExecutablePath like '%${venvScriptsDir}%'" get ProcessId /format:list`,
                        { encoding: 'utf-8', stdio: 'pipe', timeout: 10000 }
                    );
                    const pids = wmicOutput.match(/ProcessId=(\d+)/g);
                    if (pids && pids.length > 0) {
                        for (const pidMatch of pids) {
                            const pid = pidMatch.replace('ProcessId=', '');
                            this.log(`Killing process PID ${pid} using venv Python...`);
                            try {
                                execSync(`taskkill /F /PID ${pid}`, {
                                    encoding: 'utf-8', stdio: 'pipe', timeout: 5000
                                });
                            } catch {
                                // Process may have already exited
                            }
                        }
                        // Wait for processes to fully terminate
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                } catch {
                    // WMIC may not be available on all Windows versions, try taskkill directly
                    this.log('WMIC not available, trying taskkill by image name...');
                    try {
                        // As a fallback, try to kill any python.exe in our venv directory
                        // by checking if our python.exe is locked
                        execSync(
                            `powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '${this.venvDir.replace(/\\/g, '\\\\')}*' } | Stop-Process -Force"`,
                            { encoding: 'utf-8', stdio: 'pipe', timeout: 10000 }
                        );
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    } catch {
                        // No matching processes found - that's fine
                    }
                }
            } else {
                // Unix: find and kill processes using our venv Python
                try {
                    const psOutput = execSync(
                        `pgrep -f "${this.venvDir}"`,
                        { encoding: 'utf-8', stdio: 'pipe', timeout: 5000 }
                    );
                    const pids = psOutput.trim().split('\n').filter((p: string) => p.trim());
                    for (const pid of pids) {
                        this.log(`Killing process PID ${pid} using venv Python...`);
                        try {
                            execSync(`kill -9 ${pid.trim()}`, { stdio: 'pipe', timeout: 5000 });
                        } catch {
                            // Process may have already exited
                        }
                    }
                    if (pids.length > 0) {
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                } catch {
                    // No matching processes
                }
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
                const errCode = error instanceof Error ? (error as any).code : undefined;
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

        this._isReady = false;
        this.log('Cleanup complete');
    }
}
