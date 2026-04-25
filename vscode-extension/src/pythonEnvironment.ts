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
import { PUBMED_SEARCH_PACKAGE, PUBMED_SEARCH_SOURCE_URL, PUBMED_SEARCH_VERSION, compareDottedVersions } from './pubmedSearchPackage.js';
import { ZOTERO_KEEPER_PACKAGE, ZOTERO_KEEPER_SOURCE_URL, ZOTERO_KEEPER_VERSION } from './zoteroKeeperPackage.js';

interface RequiredPackage {
    name: string;
    importName: string;
    pipName: string;
    minVersion: string;
    sourceUrl: string;
}

const REQUIRED_PACKAGES: RequiredPackage[] = [
    {
        name: 'zotero-keeper',
        importName: 'zotero_mcp',
        pipName: ZOTERO_KEEPER_PACKAGE,
        minVersion: ZOTERO_KEEPER_VERSION,
        sourceUrl: ZOTERO_KEEPER_SOURCE_URL,
    },
    {
        name: 'pubmed-search-mcp',
        importName: 'pubmed_search',
        pipName: PUBMED_SEARCH_PACKAGE,
        minVersion: PUBMED_SEARCH_VERSION,
        sourceUrl: PUBMED_SEARCH_SOURCE_URL,
    },
];

// Python 3.12+ required for:
// - Type parameter syntax (PEP 695)
// - ExceptionGroup (PEP 654)
// - asyncio.TaskGroup for structured concurrency
const MIN_PYTHON_VERSION = [3, 12];
const MANAGED_SYSTEM_VENV_DIR = 'system-python-venv';
const VENV_CREATION_TIMEOUT_MS = 300000;
const PACKAGE_INSTALL_TIMEOUT_MS = 300000;

export class PythonEnvironment {
    private pythonPath: string | null = null;
    private outputChannel: vscode.OutputChannel;
    private managedVenvDir: string;

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('Zotero MCP');
        this.managedVenvDir = path.join(context.globalStorageUri.fsPath, MANAGED_SYSTEM_VENV_DIR);
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

                // Parse version like "Python 3.12.2"
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
        const venvDir = this.managedVenvDir;
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
            const installed = await this.checkPackage(pkg);
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
    private async checkPackage(pkg: RequiredPackage): Promise<boolean> {
        const pythonPath = this.pythonPath;
        if (!pythonPath) {
            return false;
        }

        return new Promise((resolve) => {
            const script = `
import json
import sys
try:
    import ${pkg.importName}
    from importlib.metadata import version, distribution
    dist = distribution("${pkg.name}")
    print(json.dumps({
        "version": version("${pkg.name}"),
        "direct_url": dist.read_text("direct_url.json") or ""
    }))
except Exception as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(1)
`;

            cp.execFile(
                pythonPath,
                ['-c', script],
                (err, stdout) => {
                    if (err) {
                        resolve(false);
                        return;
                    }

                    const raw = stdout.trim();
                    if (!raw) {
                        resolve(false);
                        return;
                    }

                    let parsed: { version?: string; direct_url?: string };
                    try {
                        parsed = JSON.parse(raw);
                    } catch {
                        resolve(false);
                        return;
                    }

                    const installedVersion = parsed.version ?? '';
                    if (!installedVersion) {
                        resolve(false);
                        return;
                    }

                    const isValid = compareDottedVersions(installedVersion, pkg.minVersion) >= 0;
                    if (!isValid) {
                        this.log(`Package ${pkg.name} is too old: ${installedVersion} < ${pkg.minVersion}`);
                        resolve(false);
                        return;
                    }

                    if (!parsed.direct_url?.includes(pkg.sourceUrl)) {
                        this.log(`Package ${pkg.name} is installed from an outdated source`);
                        resolve(false);
                        return;
                    }

                    resolve(true);
                }
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
     * Resolve uv from extension storage first, then PATH and common user install locations.
     * This keeps manual/system-Python installs fast without relying on a global pip.
     */
    private async resolveUvPath(): Promise<string | null> {
        const embeddedUv = this.getUvPath();
        if (embeddedUv) {
            return embeddedUv;
        }

        const home = os.homedir();
        const uvExe = process.platform === 'win32' ? 'uv.exe' : 'uv';
        const candidates = process.platform === 'win32'
            ? [
                path.join(home, 'AppData', 'Local', 'uv', 'bin', uvExe),
                path.join(home, '.local', 'bin', uvExe),
                path.join(home, '.cargo', 'bin', uvExe),
                path.join(process.env.LOCALAPPDATA || '', 'uv', 'bin', uvExe),
            ]
            : [
                path.join(home, '.local', 'bin', uvExe),
                path.join(home, '.cargo', 'bin', uvExe),
                '/opt/homebrew/bin/uv',
                '/usr/local/bin/uv',
            ];

        for (const candidate of candidates) {
            if (candidate && fs.existsSync(candidate) && await this.validateCommand(candidate, ['--version'])) {
                return candidate;
            }
        }

        const command = await this.resolveCommand('uv');
        return command && await this.validateCommand(command, ['--version']) ? command : null;
    }

    private async resolveCommand(command: string): Promise<string | null> {
        return new Promise((resolve) => {
            const locator = process.platform === 'win32' ? 'where' : 'which';
            cp.exec(`${locator} ${command}`, { env: this.getEnrichedEnv() }, (err, stdout) => {
                if (err || !stdout.trim()) {
                    resolve(null);
                    return;
                }
                resolve(stdout.trim().split(/\r?\n/)[0].trim());
            });
        });
    }

    private async validateCommand(command: string, args: string[]): Promise<boolean> {
        return new Promise((resolve) => {
            cp.execFile(command, args, { env: this.getEnrichedEnv(), timeout: 10000 }, (err) => {
                resolve(!err);
            });
        });
    }

    private getManagedPythonPath(): string {
        if (process.platform === 'win32') {
            return path.join(this.managedVenvDir, 'Scripts', 'python.exe');
        }
        return path.join(this.managedVenvDir, 'bin', 'python');
    }

    private getVenvRootForPython(pythonPath: string): string | null {
        const normalized = path.normalize(pythonPath);
        const parent = path.dirname(normalized);
        const venvRoot = process.platform === 'win32' && parent.toLowerCase().endsWith('scripts')
            ? path.dirname(parent)
            : parent.endsWith(`${path.sep}bin`)
                ? path.dirname(parent)
                : null;

        if (!venvRoot) {
            return null;
        }

        return fs.existsSync(path.join(venvRoot, 'pyvenv.cfg')) ? venvRoot : null;
    }

    private isWritableDirectory(dirPath: string): boolean {
        try {
            fs.accessSync(dirPath, fs.constants.W_OK);
            return true;
        } catch {
            return false;
        }
    }

    private quoteArg(value: string): string {
        return `"${value.replace(/"/g, '\\"')}"`;
    }

    private async ensureWritablePackageEnvironment(uvPath: string): Promise<string | null> {
        if (!this.pythonPath) {
            return null;
        }

        const currentVenvRoot = this.getVenvRootForPython(this.pythonPath);
        if (currentVenvRoot && this.isWritableDirectory(currentVenvRoot)) {
            this.log(`Installing into existing virtual environment: ${currentVenvRoot}`);
            return this.pythonPath;
        }

        const managedPython = this.getManagedPythonPath();
        if (fs.existsSync(managedPython) && await this.validatePython(managedPython)) {
            this.pythonPath = managedPython;
            this.log(`Using managed package environment: ${managedPython}`);
            return managedPython;
        }

        fs.mkdirSync(this.context.globalStorageUri.fsPath, { recursive: true });

        if (fs.existsSync(this.managedVenvDir)) {
            fs.rmSync(this.managedVenvDir, { recursive: true, force: true });
        }

        this.log(`Creating managed package environment at ${this.managedVenvDir}...`);
        const cmd = [
            this.quoteArg(uvPath),
            'venv',
            this.quoteArg(this.managedVenvDir),
            '--python',
            this.quoteArg(this.pythonPath),
        ].join(' ');

        const created = await this.execWithOutput(cmd, VENV_CREATION_TIMEOUT_MS, {
            UV_PYTHON_DOWNLOADS: 'automatic',
        });

        if (!created || !await this.validatePython(managedPython)) {
            this.log('Managed package environment creation failed');
            return null;
        }

        this.pythonPath = managedPython;
        this.log(`Managed package environment ready: ${managedPython}`);
        return managedPython;
    }

    private async execWithOutput(
        command: string,
        timeout: number,
        extraEnv: NodeJS.ProcessEnv = {}
    ): Promise<boolean> {
        return new Promise((resolve) => {
            this.log(`Running: ${command}`);
            const proc = cp.exec(command, {
                maxBuffer: 10 * 1024 * 1024,
                timeout,
                env: {
                    ...this.getEnrichedEnv(),
                    HOME: process.env.HOME || os.homedir(),
                    ...extraEnv,
                },
            });

            proc.stdout?.on('data', (data: string) => {
                this.outputChannel.append(data);
            });

            proc.stderr?.on('data', (data: string) => {
                this.outputChannel.append(data);
            });

            proc.on('close', (code) => {
                if (code === 0) {
                    resolve(true);
                    return;
                }

                this.log(`Command failed with code ${code}`);
                resolve(false);
            });

            proc.on('error', (error) => {
                this.log(`Command failed: ${error.message}`);
                resolve(false);
            });
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

        const packages = REQUIRED_PACKAGES.map(p => this.quoteArg(p.pipName)).join(' ');

        // Use uv for package installation (required)
        const uvPath = await this.resolveUvPath();
        if (!uvPath) {
            this.log('uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/');
            return false;
        }

        const installPython = await this.ensureWritablePackageEnvironment(uvPath);
        if (!installPython) {
            return false;
        }

        const cmd = `${this.quoteArg(uvPath)} pip install --upgrade --force-reinstall --python ${this.quoteArg(installPython)} ${packages}`;
        this.log('Using uv for package installation in an isolated environment');

        const success = await this.execWithOutput(cmd, PACKAGE_INSTALL_TIMEOUT_MS, {
            VIRTUAL_ENV: this.getVenvRootForPython(installPython) || this.managedVenvDir,
        });
        if (success) {
            this.log('Packages installed successfully');
            return true;
        }

        this.log('Installation failed');
        return false;
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
