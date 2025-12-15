/**
 * Embedded Python Manager
 * 
 * Downloads and manages a standalone Python environment for non-technical users.
 * No system Python installation required!
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as https from 'https';
import * as http from 'http';

// Python standalone download URLs (from indygreg/python-build-standalone)
// Using "install_only_stripped" variants - smallest size with pip included
const PYTHON_DOWNLOADS: Record<string, { url: string; extractedName: string }> = {
    'win32-x64': {
        url: 'https://github.com/indygreg/python-build-standalone/releases/download/20241206/cpython-3.11.11+20241206-x86_64-pc-windows-msvc-install_only_stripped.tar.gz',
        extractedName: 'python'
    },
    'linux-x64': {
        url: 'https://github.com/indygreg/python-build-standalone/releases/download/20241206/cpython-3.11.11+20241206-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz',
        extractedName: 'python'
    },
    'darwin-x64': {
        url: 'https://github.com/indygreg/python-build-standalone/releases/download/20241206/cpython-3.11.11+20241206-x86_64-apple-darwin-install_only_stripped.tar.gz',
        extractedName: 'python'
    },
    'darwin-arm64': {
        url: 'https://github.com/indygreg/python-build-standalone/releases/download/20241206/cpython-3.11.11+20241206-aarch64-apple-darwin-install_only_stripped.tar.gz',
        extractedName: 'python'
    },
};

// Required packages to install
// Note: zotero-keeper must be uploaded to PyPI first!
const REQUIRED_PACKAGES = [
    'zotero-keeper>=1.7.0',
    'pubmed-search-mcp>=0.1.8',
];

export class EmbeddedPythonManager {
    private context: vscode.ExtensionContext;
    private outputChannel: vscode.OutputChannel;
    private pythonDir: string;
    private pythonBinary: string;
    private _isReady: boolean = false;
    private _setupInProgress: boolean = false;  // Prevent concurrent setup

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.outputChannel = vscode.window.createOutputChannel('Zotero MCP Setup');
        
        // Setup paths
        this.pythonDir = path.join(context.globalStorageUri.fsPath, 'python');
        this.pythonBinary = this.getPythonBinaryPath();
        
        // Check if already ready (synchronous check)
        this._isReady = this.checkReadySync();
    }

    /**
     * Get the platform key for downloads
     */
    private getPlatformKey(): string {
        const platform = process.platform;
        const arch = process.arch;
        return `${platform}-${arch}`;
    }

    /**
     * Get Python binary path based on platform
     */
    private getPythonBinaryPath(): string {
        const platform = process.platform;
        if (platform === 'win32') {
            return path.join(this.pythonDir, 'python', 'python.exe');
        } else {
            return path.join(this.pythonDir, 'python', 'bin', 'python3');
        }
    }

    /**
     * Synchronous check if Python exists
     */
    private checkReadySync(): boolean {
        return fs.existsSync(this.pythonBinary);
    }

    /**
     * Check if embedded Python is ready (sync for quick checks)
     */
    isReady(): boolean {
        return this._isReady;
    }

    /**
     * Full async check if Python and packages are ready
     */
    async verifyReady(): Promise<boolean> {
        if (!fs.existsSync(this.pythonBinary)) {
            this._isReady = false;
            return false;
        }

        try {
            const { execSync } = await import('child_process');
            execSync(`"${this.pythonBinary}" --version`, { encoding: 'utf-8', stdio: 'pipe' });
            
            // Check if packages are installed
            execSync(
                `"${this.pythonBinary}" -c "import zotero_mcp; import pubmed_search"`,
                { encoding: 'utf-8', stdio: 'pipe' }
            );
            
            this._isReady = true;
            return true;
        } catch {
            this._isReady = false;
            return false;
        }
    }

    /**
     * Get Python path (for MCP server)
     */
    getPythonPath(): string {
        return this.pythonBinary;
    }

    /**
     * Get Python version
     */
    async getPythonVersion(): Promise<string | undefined> {
        if (!this._isReady) {
            return undefined;
        }
        
        try {
            const { execSync } = await import('child_process');
            const output = execSync(`"${this.pythonBinary}" --version`, { 
                encoding: 'utf-8',
                stdio: 'pipe'
            });
            return output.trim().replace('Python ', '');
        } catch {
            return undefined;
        }
    }

    /**
     * Ensure embedded Python is ready (main entry point)
     * Downloads and installs if needed
     */
    async ensureReady(): Promise<string> {
        // Check if already set up
        if (await this.verifyReady()) {
            this.log('Embedded Python is already ready');
            return this.pythonBinary;
        }

        // Prevent concurrent setup attempts
        if (this._setupInProgress) {
            this.log('Setup already in progress, waiting...');
            // Wait for existing setup to complete
            while (this._setupInProgress) {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            if (this._isReady) {
                return this.pythonBinary;
            }
            throw new Error('Concurrent setup failed');
        }

        this._setupInProgress = true;

        try {
            // Need to set up - show progress
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
                throw new Error('Failed to set up embedded Python');
            }
        );
        } finally {
            this._setupInProgress = false;
        }
    }

    /**
     * Setup embedded Python environment
     */
    async setup(progress: vscode.Progress<{ message?: string; increment?: number }>): Promise<boolean> {
        const platformKey = this.getPlatformKey();
        const downloadInfo = PYTHON_DOWNLOADS[platformKey];

        if (!downloadInfo) {
            vscode.window.showErrorMessage(
                `Unsupported platform: ${platformKey}. Please install Python 3.11+ manually.`
            );
            return false;
        }

        try {
            // Create directories
            fs.mkdirSync(this.pythonDir, { recursive: true });

            // Step 1: Download Python
            progress.report({ message: 'Downloading Python (~35MB)...', increment: 0 });
            this.log(`Downloading Python for ${platformKey}...`);
            this.log(`URL: ${downloadInfo.url}`);
            
            const tarPath = path.join(this.pythonDir, 'python.tar.gz');
            await this.downloadFile(downloadInfo.url, tarPath, (percent) => {
                progress.report({ message: `Downloading Python... ${percent}%` });
            });

            // Step 2: Extract
            progress.report({ message: 'Extracting Python...', increment: 40 });
            this.log('Extracting Python...');
            await this.extractTarGz(tarPath, this.pythonDir);
            
            // Clean up tar file
            fs.unlinkSync(tarPath);

            // Step 3: Install pip (if needed) and packages
            progress.report({ message: 'Installing MCP packages...', increment: 60 });
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
     * Download file with progress and redirect handling
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
                    // Handle redirects
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

                request.setTimeout(60000, () => {
                    request.destroy();
                    reject(new Error('Download timeout'));
                });
            };

            doRequest(url);
        });
    }

    /**
     * Extract tar.gz file
     */
    private async extractTarGz(tarPath: string, destDir: string): Promise<void> {
        const { execSync } = await import('child_process');
        
        this.log(`Extracting ${tarPath} to ${destDir}`);
        
        if (process.platform === 'win32') {
            // On Windows, use PowerShell's tar which handles paths better
            // Or use the built-in tar with proper escaping
            try {
                // Try PowerShell first (more reliable on Windows)
                execSync(
                    `powershell -Command "tar -xzf '${tarPath.replace(/'/g, "''")}' -C '${destDir.replace(/'/g, "''")}'"`,
                    { encoding: 'utf-8', stdio: 'pipe', timeout: 120000 }
                );
            } catch (psError) {
                this.log(`PowerShell tar failed, trying cmd: ${psError}`);
                // Fallback: use cmd with short paths if available
                execSync(`tar -xzf "${tarPath}" -C "${destDir}"`, {
                    encoding: 'utf-8',
                    stdio: 'pipe',
                    timeout: 120000,
                    shell: 'cmd.exe'
                });
            }
        } else {
            // macOS and Linux
            execSync(`tar -xzf "${tarPath}" -C "${destDir}"`, { 
                encoding: 'utf-8',
                stdio: 'pipe',
                timeout: 120000
            });
        }
        
        this.log('Extraction complete');
    }

    /**
     * Install required Python packages
     */
    private async installPackages(onProgress?: (msg: string) => void): Promise<void> {
        const { execSync } = await import('child_process');
        
        // Ensure pip is available
        try {
            this.log('Ensuring pip is available...');
            execSync(`"${this.pythonBinary}" -m ensurepip --default-pip`, {
                encoding: 'utf-8',
                stdio: 'pipe',
                timeout: 60000
            });
        } catch (e) {
            // pip might already be installed
            this.log(`ensurepip note: ${e}`);
        }

        // Skip pip upgrade - it can cause issues with the bundled pip
        // The bundled pip is functional enough for our needs
        this.log('Using bundled pip (skipping upgrade to avoid conflicts)...');
        onProgress?.('Preparing pip...');

        // Install packages one by one for better progress feedback
        for (const pkg of REQUIRED_PACKAGES) {
            this.log(`Installing: ${pkg}`);
            onProgress?.(`Installing ${pkg.split('[')[0]}...`);
            
            try {
                execSync(`"${this.pythonBinary}" -m pip install "${pkg}"`, {
                    encoding: 'utf-8',
                    cwd: this.pythonDir,
                    stdio: 'pipe'
                });
            } catch (error) {
                this.log(`Error installing ${pkg}: ${error}`);
                throw error;
            }
        }
        
        this.log('All packages installed successfully');
    }

    /**
     * Log message
     */
    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
        console.log(`[EmbeddedPython] ${message}`);
    }

    /**
     * Show output channel
     */
    showOutput(): void {
        this.outputChannel.show();
    }

    /**
     * Clean up embedded Python (for reinstall)
     */
    async cleanup(): Promise<void> {
        this.log('Cleaning up embedded Python...');
        if (fs.existsSync(this.pythonDir)) {
            fs.rmSync(this.pythonDir, { recursive: true, force: true });
        }
        this._isReady = false;
        this.log('Cleanup complete');
    }
}
