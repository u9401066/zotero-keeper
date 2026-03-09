/**
 * Python Environment Manager
 *
 * Handles Python detection, version checking, and package installation.
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

const REQUIRED_PACKAGES = [
    { name: 'zotero-keeper', importName: 'zotero_mcp', pipName: 'zotero-keeper' },
    { name: 'pubmed-search-mcp', importName: 'pubmed_search', pipName: 'pubmed-search-mcp' },
];

// Python 3.12+ required for:
// - Type parameter syntax (PEP 695)
// - ExceptionGroup (PEP 654)
// - asyncio.TaskGroup for structured concurrency
const MIN_PYTHON_VERSION = [3, 12];

export class PythonEnvironment {
    private pythonPath: string | null = null;
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('Zotero MCP');
    }

    /**
     * Get the current Python path
     */
    getPythonPath(): string | null {
        return this.pythonPath;
    }

    /**
     * Ensure Python is available and meets requirements
     */
    async ensurePython(): Promise<string | null> {
        this.log('Looking for Python...');

        // 1. Check user-configured path first
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const configuredPath = config.get<string>('pythonPath');

        if (configuredPath && await this.validatePython(configuredPath)) {
            this.pythonPath = configuredPath;
            this.log(`Using configured Python: ${configuredPath}`);
            return this.pythonPath;
        }

        // 2. Try to use Python extension's interpreter
        const pythonExtPath = await this.getPythonExtensionInterpreter();
        if (pythonExtPath && await this.validatePython(pythonExtPath)) {
            this.pythonPath = pythonExtPath;
            this.log(`Using Python extension interpreter: ${pythonExtPath}`);
            return this.pythonPath;
        }

        // 3. Try common Python commands (with enriched PATH on macOS)
        const candidates = ['python3', 'python', 'py'];
        for (const cmd of candidates) {
            const resolved = await this.resolvePythonCommand(cmd);
            if (resolved && await this.validatePython(resolved)) {
                this.pythonPath = resolved;
                this.log(`Using system Python: ${resolved}`);
                return this.pythonPath;
            }
        }

        // 4. Try well-known paths on macOS (GUI apps don't inherit shell PATH)
        if (process.platform === 'darwin') {
            const macPython = await this.findMacPython();
            if (macPython) {
                this.pythonPath = macPython;
                this.log(`Using macOS Python: ${macPython}`);
                return this.pythonPath;
            }
        }

        // 4. Create virtual environment in extension storage (fallback)
        const venvPath = await this.createVirtualEnvironment();
        if (venvPath && await this.validatePython(venvPath)) {
            this.pythonPath = venvPath;
            this.log(`Using extension virtual environment: ${venvPath}`);
            return this.pythonPath;
        }

        this.log('ERROR: No suitable Python found');
        return null;
    }

    /**
     * Try to get Python interpreter from Python extension
     */
    private async getPythonExtensionInterpreter(): Promise<string | null> {
        try {
            const pythonExt = vscode.extensions.getExtension('ms-python.python');
            if (!pythonExt) {
                return null;
            }

            if (!pythonExt.isActive) {
                await pythonExt.activate();
            }

            const api = pythonExt.exports;
            if (api && api.settings) {
                const interpreterPath = api.settings.getExecutionDetails()?.execCommand;
                if (interpreterPath && interpreterPath.length > 0) {
                    return interpreterPath[0];
                }
            }
        } catch (e) {
            this.log(`Warning: Could not get Python extension interpreter: ${e}`);
        }
        return null;
    }

    /**
     * Resolve a Python command to full path.
     * On macOS, enriches PATH to include common locations that
     * GUI-launched apps don't inherit from shell profiles.
     */
    private async resolvePythonCommand(cmd: string): Promise<string | null> {
        return new Promise((resolve) => {
            const which = process.platform === 'win32' ? 'where' : 'which';
            const env = this.getEnrichedEnv();
            cp.exec(`${which} ${cmd}`, { env }, (err, stdout) => {
                if (err || !stdout.trim()) {
                    resolve(null);
                } else {
                    // Take first result (in case of multiple)
                    resolve(stdout.trim().split('\n')[0].trim());
                }
            });
        });
    }

    /**
     * Search well-known macOS Python installation paths.
     * Covers: Homebrew (Intel & Apple Silicon), pyenv, official installer,
     * Xcode Command Line Tools, and Framework installs.
     */
    private async findMacPython(): Promise<string | null> {
        const home = os.homedir();
        const knownPaths = [
            // Homebrew - Apple Silicon
            '/opt/homebrew/bin/python3',
            // Homebrew - Intel
            '/usr/local/bin/python3',
            // pyenv
            path.join(home, '.pyenv', 'shims', 'python3'),
            // Official Python.org installer
            '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
            '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',
            // Xcode Command Line Tools
            '/usr/bin/python3',
        ];

        for (const p of knownPaths) {
            if (fs.existsSync(p)) {
                this.log(`Checking macOS path: ${p}`);
                if (await this.validatePython(p)) {
                    return p;
                }
            }
        }
        return null;
    }

    /**
     * Get PATH environment enriched with common macOS locations.
     */
    private getEnrichedEnv(): NodeJS.ProcessEnv {
        if (process.platform !== 'darwin') {
            return process.env;
        }
        const home = os.homedir();
        const extraPaths = [
            '/opt/homebrew/bin',
            '/usr/local/bin',
            path.join(home, '.pyenv', 'shims'),
            path.join(home, '.local', 'bin'),
        ].filter(p => fs.existsSync(p));

        if (extraPaths.length === 0) {
            return process.env;
        }
        return {
            ...process.env,
            PATH: [...extraPaths, process.env.PATH || ''].join(':'),
        };
    }

    /**
     * Validate Python version
     */
    private async validatePython(pythonPath: string): Promise<boolean> {
        return new Promise((resolve) => {
            cp.exec(`"${pythonPath}" --version`, (err, stdout) => {
                if (err) {
                    resolve(false);
                    return;
                }

                // Parse version like "Python 3.11.2"
                const match = stdout.match(/Python (\d+)\.(\d+)/);
                if (!match) {
                    resolve(false);
                    return;
                }

                const major = parseInt(match[1]);
                const minor = parseInt(match[2]);

                const isValid = major > MIN_PYTHON_VERSION[0] ||
                    (major === MIN_PYTHON_VERSION[0] && minor >= MIN_PYTHON_VERSION[1]);

                if (isValid) {
                    this.log(`Python ${major}.${minor} found at ${pythonPath}`);
                } else {
                    this.log(`Python ${major}.${minor} too old (need ${MIN_PYTHON_VERSION.join('.')}+)`);
                }

                resolve(isValid);
            });
        });
    }

    /**
     * Get Python version string
     */
    async getPythonVersion(): Promise<string | null> {
        if (!this.pythonPath) {
            return null;
        }

        return new Promise((resolve) => {
            cp.exec(`"${this.pythonPath}" --version`, (err, stdout) => {
                if (err) {
                    resolve(null);
                } else {
                    resolve(stdout.trim().replace('Python ', ''));
                }
            });
        });
    }

    /**
     * Create virtual environment in extension storage
     */
    private async createVirtualEnvironment(): Promise<string | null> {
        const venvDir = path.join(this.context.globalStorageUri.fsPath, 'venv');
        const pythonInVenv = process.platform === 'win32'
            ? path.join(venvDir, 'Scripts', 'python.exe')
            : path.join(venvDir, 'bin', 'python');

        // Check if venv already exists
        if (fs.existsSync(pythonInVenv)) {
            return pythonInVenv;
        }

        // Find system Python to create venv
        const systemPython = await this.resolvePythonCommand('python3') ||
                            await this.resolvePythonCommand('python');

        if (!systemPython) {
            return null;
        }

        this.log(`Creating virtual environment at ${venvDir}...`);

        return new Promise((resolve) => {
            cp.exec(`"${systemPython}" -m venv "${venvDir}"`, (err) => {
                if (err) {
                    this.log(`Failed to create venv: ${err.message}`);
                    resolve(null);
                } else {
                    this.log('Virtual environment created');
                    resolve(pythonInVenv);
                }
            });
        });
    }

    /**
     * Check if required packages are installed
     */
    async checkPackages(): Promise<boolean> {
        if (!this.pythonPath) {
            return false;
        }

        for (const pkg of REQUIRED_PACKAGES) {
            const installed = await this.checkPackage(pkg.importName);
            if (!installed) {
                this.log(`Package ${pkg.name} is not installed`);
                return false;
            }
        }

        this.log('All required packages are installed');
        return true;
    }

    /**
     * Check if a single package is installed
     */
    private async checkPackage(importName: string): Promise<boolean> {
        return new Promise((resolve) => {
            cp.exec(
                `"${this.pythonPath}" -c "import ${importName}"`,
                (err) => resolve(!err)
            );
        });
    }

    /**
     * Get the path to uv executable in extension storage
     */
    private getUvPath(): string | null {
        const storagePath = this.context.globalStorageUri.fsPath;
        const uvDir = path.join(storagePath, 'uv');
        const uvExe = process.platform === 'win32' ? 'uv.exe' : 'uv';
        const uvPath = path.join(uvDir, uvExe);
        return fs.existsSync(uvPath) ? uvPath : null;
    }

    /**
     * Install required packages
     */
    async installPackages(): Promise<boolean> {
        if (!this.pythonPath) {
            return false;
        }

        this.outputChannel.show();
        this.log('Installing required packages...');

        const packages = REQUIRED_PACKAGES.map(p => p.pipName).join(' ');

        // Use uv for package installation (required)
        const uvPath = this.getUvPath();
        if (!uvPath) {
            this.log('❌ uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/');
            return false;
        }

        const cmd = `"${uvPath}" pip install --upgrade --python "${this.pythonPath}" ${packages}`;
        this.log('Using uv for package installation');

        return new Promise((resolve) => {
            this.log(`Running: ${cmd}`);

            const proc = cp.exec(cmd, { maxBuffer: 10 * 1024 * 1024 });

            proc.stdout?.on('data', (data: string) => {
                this.outputChannel.append(data);
            });

            proc.stderr?.on('data', (data: string) => {
                this.outputChannel.append(data);
            });

            proc.on('close', (code) => {
                if (code === 0) {
                    this.log('✅ Packages installed successfully');
                    resolve(true);
                } else {
                    this.log(`❌ Installation failed with code ${code}`);
                    resolve(false);
                }
            });
        });
    }

    /**
     * Log message to output channel
     */
    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
        console.log(`[ZoteroMCP] ${message}`);
    }

    /**
     * Dispose resources
     */
    dispose(): void {
        this.outputChannel.dispose();
    }
}
