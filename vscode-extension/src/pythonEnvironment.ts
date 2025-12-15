/**
 * Python Environment Manager
 * 
 * Handles Python detection, version checking, and package installation.
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

const REQUIRED_PACKAGES = [
    { name: 'zotero-keeper', importName: 'zotero_mcp', pipName: 'zotero-keeper[all]' },
    { name: 'pubmed-search-mcp', importName: 'pubmed_search', pipName: 'pubmed-search-mcp[mcp]' },
];

const MIN_PYTHON_VERSION = [3, 11];

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

        // 3. Try common Python commands
        const candidates = ['python3', 'python', 'py'];
        for (const cmd of candidates) {
            const resolved = await this.resolvePythonCommand(cmd);
            if (resolved && await this.validatePython(resolved)) {
                this.pythonPath = resolved;
                this.log(`Using system Python: ${resolved}`);
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
     * Resolve a Python command to full path
     */
    private async resolvePythonCommand(cmd: string): Promise<string | null> {
        return new Promise((resolve) => {
            const which = process.platform === 'win32' ? 'where' : 'which';
            cp.exec(`${which} ${cmd}`, (err, stdout) => {
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
     * Install required packages
     */
    async installPackages(): Promise<boolean> {
        if (!this.pythonPath) {
            return false;
        }

        this.outputChannel.show();
        this.log('Installing required packages...');

        const packages = REQUIRED_PACKAGES.map(p => p.pipName).join(' ');
        const cmd = `"${this.pythonPath}" -m pip install --upgrade ${packages}`;

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
