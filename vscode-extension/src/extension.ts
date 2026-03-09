/**
 * Zotero + PubMed MCP Extension
 *
 * Provides AI-powered research assistant capabilities by integrating
 * Zotero reference management and PubMed literature search with GitHub Copilot.
 *
 * Self-contained: Downloads Python automatically for non-technical users.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { PythonEnvironment } from './pythonEnvironment';
import { UvPythonManager } from './uvPythonManager';
import { ZoteroMcpServerProvider } from './mcpProvider';
import { StatusBarManager } from './statusBar';

let pythonEnv: PythonEnvironment;
let uvPython: UvPythonManager;
let mcpProvider: ZoteroMcpServerProvider;
let statusBar: StatusBarManager;
let extensionContext: vscode.ExtensionContext;

// The resolved Python path (either system or embedded)
let resolvedPythonPath: string | undefined;

// Context keys for walkthrough completion tracking
const CONTEXT_PYTHON_READY = 'zoteroMcp.pythonReady';
const CONTEXT_PACKAGES_READY = 'zoteroMcp.packagesReady';
const CONTEXT_ZOTERO_CONNECTED = 'zoteroMcp.zoteroConnected';
const FIRST_ACTIVATION_KEY = 'zoteroMcp.firstActivation';
const SKILLS_INSTALLED_KEY = 'zoteroMcp.skillsInstalled';

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Zotero MCP extension is activating...');
    extensionContext = context;

    // Initialize components
    pythonEnv = new PythonEnvironment(context);
    uvPython = new UvPythonManager(context);
    statusBar = new StatusBarManager();

    // Initialize status bar with context for statistics
    statusBar.initialize(context);

    // Register commands first (so they're available even if setup fails)
    registerCommands(context);

    // Show initial status
    statusBar.setStatus('initializing', 'Zotero MCP: Initializing...');

    try {
        // Step 1: Ensure Python is available (try system first, then embedded)
        resolvedPythonPath = await ensurePythonEnvironment();

        if (!resolvedPythonPath) {
            statusBar.setStatus('error', 'Zotero MCP: Python setup failed');
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, false);
            showFirstTimeWalkthrough(context);
            return;
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);

        // Step 2: Check/install required packages (handled by embedded Python if used)
        const packagesReady = await ensurePackagesInstalled();

        if (!packagesReady) {
            statusBar.setStatus('error', 'Zotero MCP: Package install failed');
            await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
            showFirstTimeWalkthrough(context);
            return;
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);

        // Step 3: Register MCP server provider
        mcpProvider = new ZoteroMcpServerProvider(resolvedPythonPath);

        const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'zotero-mcp.servers',
            mcpProvider
        );
        context.subscriptions.push(providerDisposable);

        // Step 4: Check Zotero connection (non-blocking)
        checkAndUpdateZoteroStatus();

        // Step 5: Install Copilot skills/instructions if needed
        await installCopilotInstructions(context);

        // Step 6: Update status
        statusBar.setStatus('ready', 'Zotero MCP: Ready');

        // Show walkthrough on first activation
        showFirstTimeWalkthrough(context);

        console.log('Zotero MCP extension activated successfully');

    } catch (error) {
        console.error('Zotero MCP activation error:', error);
        statusBar.setStatus('error', 'Zotero MCP: Activation failed');
        vscode.window.showErrorMessage(`Zotero MCP activation failed: ${error}`);
    }
}

/**
 * Ensure Python is available - uses uv-managed Python by default for consistency
 *
 * Priority (when useEmbeddedPython = true, the default):
 *   1. Use uv-managed Python 3.11 (guaranteed compatible, self-contained)
 *   2. Fall back to system Python only if uv fails
 *
 * Priority (when useEmbeddedPython = false):
 *   1. Use system Python (user's responsibility to ensure compatibility)
 */
async function ensurePythonEnvironment(): Promise<string | undefined> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const useEmbedded = config.get<boolean>('useEmbeddedPython', true);

    // When useEmbeddedPython is true (default), prioritize uv-managed Python
    // This ensures consistent behavior regardless of user's system Python version
    if (useEmbedded) {
        console.log('Using uv-managed Python (useEmbeddedPython=true)...');
        statusBar.setStatus('installing', 'Zotero MCP: Setting up Python environment...');

        try {
            // UvPythonManager.ensureReady() handles uv download + Python 3.11 install + packages
            const uvPythonPath = await uvPython.ensureReady();
            console.log('uv-managed Python ready:', uvPythonPath);
            return uvPythonPath;
        } catch (error) {
            console.error('Failed to set up Python with uv:', error);

            // Fall back to system Python if uv fails
            console.log('Falling back to system Python...');
            const systemPython = await pythonEnv.ensurePython();
            if (systemPython) {
                console.log('Using system Python as fallback:', systemPython);
                vscode.window.showWarningMessage(
                    'Using system Python as fallback. For best results, ensure Python 3.12+ is installed.',
                    'OK'
                );
                return systemPython;
            }

            // Both uv and system Python failed
            vscode.window.showErrorMessage(
                `Failed to set up Python environment: ${error}`,
                'Retry', 'Install Python Manually'
            ).then(choice => {
                if (choice === 'Retry') {
                    vscode.commands.executeCommand('zoteroMcp.setupWizard');
                } else if (choice === 'Install Python Manually') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
                }
            });
            return undefined;
        }
    }

    // When useEmbeddedPython is false, use system Python only
    console.log('Using system Python (useEmbeddedPython=false)...');
    const systemPython = await pythonEnv.ensurePython();

    if (systemPython) {
        console.log('Using system Python:', systemPython);
        return systemPython;
    }

    // No system Python found and embedded is disabled
    vscode.window.showErrorMessage(
        'Python not found. Install Python 3.12+ or enable embedded Python in settings.',
        'Download Python', 'Enable Embedded Python'
    ).then(choice => {
        if (choice === 'Download Python') {
            vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
        } else if (choice === 'Enable Embedded Python') {
            config.update('useEmbeddedPython', true, vscode.ConfigurationTarget.Global);
            vscode.commands.executeCommand('zoteroMcp.setupWizard');
        }
    });

    return undefined;
}

/**
 * Ensure packages are installed
 */
async function ensurePackagesInstalled(): Promise<boolean> {
    // If using uv-managed Python, packages were installed during setup
    if (uvPython.isReady()) {
        return true;
    }

    // Using system Python - check and install packages
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const autoInstall = config.get<boolean>('autoInstallPackages', true);

    let packagesInstalled = await pythonEnv.checkPackages();

    if (!packagesInstalled) {
        if (autoInstall) {
            statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
            packagesInstalled = await pythonEnv.installPackages();
        } else {
            const choice = await vscode.window.showInformationMessage(
                'Zotero MCP requires Python packages (zotero-keeper, pubmed-search-mcp). Install now?',
                'Install', 'Later'
            );
            if (choice === 'Install') {
                statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                packagesInstalled = await pythonEnv.installPackages();
            }
        }
    }

    return packagesInstalled;
}

/**
 * Show walkthrough on first activation
 */
function showFirstTimeWalkthrough(context: vscode.ExtensionContext): void {
    const isFirstActivation = context.globalState.get<boolean>(FIRST_ACTIVATION_KEY, true);

    if (isFirstActivation) {
        // Mark as not first time anymore
        context.globalState.update(FIRST_ACTIVATION_KEY, false);

        // Open walkthrough
        vscode.commands.executeCommand(
            'workbench.action.openWalkthrough',
            'u9401066.vscode-zotero-mcp#zoteroMcp.welcome',
            false
        );
    }
}

/**
 * Check Zotero connection and update context
 */
async function checkAndUpdateZoteroStatus(): Promise<boolean> {
    const connected = await checkZoteroConnection();
    await vscode.commands.executeCommand('setContext', CONTEXT_ZOTERO_CONNECTED, connected);
    return connected;
}

/**
 * Install Copilot instructions and skills to workspace (if not already installed)
 * IMPORTANT: Never overwrite existing user files automatically!
 */
async function installCopilotInstructions(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        return; // No workspace open
    }

    const githubDir = path.join(workspaceFolder.uri.fsPath, '.github');
    const agentsDir = path.join(githubDir, 'agents');
    const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
    const workflowDest = path.join(githubDir, 'zotero-research-workflow.md');
    const agentDest = path.join(agentsDir, 'research.agent.md');

    // Check if research agent already installed (primary marker for v0.5.15+)
    if (fs.existsSync(agentDest)) {
        const content = fs.readFileSync(agentDest, 'utf-8');
        if (content.includes('PubMed') && content.includes('Zotero')) {
            return; // Already installed, don't touch anything
        }
    }

    // Fallback: check legacy workflow file
    if (fs.existsSync(workflowDest) && !fs.existsSync(agentDest)) {
        const content = fs.readFileSync(workflowDest, 'utf-8');
        if (content.includes('Zotero + PubMed MCP')) {
            // Legacy install exists, upgrade to agent format
            await installResearchAgent(context, githubDir, agentsDir, agentDest);
            return;
        }
    }

    // Check if user has existing copilot-instructions.md
    if (fs.existsSync(instructionsPath)) {
        // User has their own instructions, don't overwrite!
        // Only offer to add our research agent
        const choice = await vscode.window.showInformationMessage(
            'Would you like to add Zotero+PubMed research agent? (Your existing files will not be modified)',
            'Yes', 'No'
        );

        if (choice !== 'Yes') {
            return;
        }
    }

    try {
        // Create directories
        if (!fs.existsSync(githubDir)) {
            fs.mkdirSync(githubDir, { recursive: true });
        }

        const extensionPath = context.extensionPath;

        // Install copilot-instructions.md (only if user doesn't have one)
        const sourceInstructions = path.join(extensionPath, 'resources', 'skills', 'copilot-instructions.md');
        if (fs.existsSync(sourceInstructions) && !fs.existsSync(instructionsPath)) {
            fs.copyFileSync(sourceInstructions, instructionsPath);
            console.log('Installed Copilot instructions');
        }

        // Install research agent
        await installResearchAgent(context, githubDir, agentsDir, agentDest);

        // Mark as installed
        context.globalState.update(SKILLS_INSTALLED_KEY, true);

    } catch (error) {
        console.error('Failed to install Copilot instructions:', error);
    }
}

/**
 * Install research agent to .github/agents/
 */
async function installResearchAgent(
    context: vscode.ExtensionContext,
    githubDir: string,
    agentsDir: string,
    agentDest: string
): Promise<void> {
    if (!fs.existsSync(agentsDir)) {
        fs.mkdirSync(agentsDir, { recursive: true });
    }

    const sourceAgent = path.join(context.extensionPath, 'resources', 'agents', 'research.agent.md');
    if (fs.existsSync(sourceAgent) && !fs.existsSync(agentDest)) {
        fs.copyFileSync(sourceAgent, agentDest);
        console.log('Installed research agent');
    }
}

/**
 * Register extension commands
 */
function registerCommands(context: vscode.ExtensionContext): void {
    // Setup Wizard - one-click setup
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.setupWizard', async () => {
            await runSetupWizard();
        })
    );

    // Check Zotero connection
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.checkConnection', async () => {
            const connected = await checkAndUpdateZoteroStatus();
            if (connected) {
                vscode.window.showInformationMessage('✅ Zotero is running and accessible!');
            } else {
                const config = vscode.workspace.getConfiguration('zoteroMcp');
                const host = config.get<string>('zoteroHost', 'localhost');
                const port = config.get<number>('zoteroPort', 23119);
                const choice = await vscode.window.showWarningMessage(
                    `❌ Cannot connect to Zotero at ${host}:${port}. Make sure Zotero is running.`,
                    'Retry', 'Download Zotero', 'Open Settings'
                );
                if (choice === 'Retry') {
                    vscode.commands.executeCommand('zoteroMcp.checkConnection');
                } else if (choice === 'Download Zotero') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.zotero.org/download/'));
                } else if (choice === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp.zotero');
                }
            }
        })
    );

    // Install packages
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.installPackages', async () => {
            statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
            const success = await pythonEnv.installPackages();
            if (success) {
                statusBar.setStatus('ready', 'Zotero MCP: Ready');
                await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);
                vscode.window.showInformationMessage('✅ Python packages installed successfully!');
                // Refresh MCP servers
                mcpProvider?.refresh();
            } else {
                statusBar.setStatus('error', 'Zotero MCP: Install failed');
                await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
                vscode.window.showErrorMessage('❌ Failed to install packages. Check the output for details.');
            }
        })
    );

    // Show status
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.showStatus', async () => {
            const status = await getExtensionStatus();
            const panel = vscode.window.createWebviewPanel(
                'zoteroMcpStatus',
                'Zotero MCP Status',
                vscode.ViewColumn.One,
                {}
            );
            panel.webview.html = getStatusWebviewContent(status);
        })
    );

    // Open settings
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp');
        })
    );

    // Open Zotero application
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.openZotero', async () => {
            // Try to open Zotero via URL scheme (works on most platforms)
            vscode.env.openExternal(vscode.Uri.parse('zotero://'));
        })
    );

    // Reinstall embedded Python
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.reinstallPython', async () => {
            const confirm = await vscode.window.showWarningMessage(
                'This will remove and reinstall the embedded Python environment. Continue?',
                'Yes', 'No'
            );

            if (confirm === 'Yes') {
                statusBar.setStatus('installing', 'Zotero MCP: Reinstalling Python...');

                try {
                    await uvPython.cleanup();
                    const newPath = await uvPython.ensureReady();

                    if (newPath) {
                        resolvedPythonPath = newPath;
                        mcpProvider?.setPythonPath(newPath);
                        statusBar.setStatus('ready', 'Zotero MCP: Ready');
                        vscode.window.showInformationMessage('✅ Python environment reinstalled successfully!');
                    }
                } catch (error) {
                    statusBar.setStatus('error', 'Zotero MCP: Reinstall failed');
                    vscode.window.showErrorMessage(`Failed to reinstall: ${error}`);
                }
            }
        })
    );

    // Install/Update Copilot Skills
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.installSkills', async () => {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showWarningMessage('Please open a workspace folder first.');
                return;
            }

            const githubDir = path.join(workspaceFolder.uri.fsPath, '.github');
            const agentsDir = path.join(githubDir, 'agents');
            const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
            const agentDest = path.join(agentsDir, 'research.agent.md');

            // Create directories
            if (!fs.existsSync(githubDir)) {
                fs.mkdirSync(githubDir, { recursive: true });
            }

            const extensionPath = context.extensionPath;
            const sourceInstructions = path.join(extensionPath, 'resources', 'skills', 'copilot-instructions.md');
            const sourceAgent = path.join(extensionPath, 'resources', 'agents', 'research.agent.md');

            let installed = 0;
            let skipped = 0;

            // Handle copilot-instructions.md - NEVER overwrite without explicit consent
            if (fs.existsSync(instructionsPath)) {
                const content = fs.readFileSync(instructionsPath, 'utf-8');
                if (content.includes('Zotero + PubMed MCP')) {
                    // It's our file, safe to update
                    if (fs.existsSync(sourceInstructions)) {
                        fs.copyFileSync(sourceInstructions, instructionsPath);
                        installed++;
                    }
                } else {
                    // User's own file - DO NOT TOUCH
                    vscode.window.showInformationMessage(
                        'ℹ️ Your existing copilot-instructions.md was preserved (not modified).'
                    );
                    skipped++;
                }
            } else if (fs.existsSync(sourceInstructions)) {
                fs.copyFileSync(sourceInstructions, instructionsPath);
                installed++;
            }

            // Handle research.agent.md
            if (fs.existsSync(agentDest)) {
                const content = fs.readFileSync(agentDest, 'utf-8');
                if (content.includes('PubMed') && content.includes('Zotero')) {
                    // It's our file, safe to update
                    if (fs.existsSync(sourceAgent)) {
                        fs.copyFileSync(sourceAgent, agentDest);
                        installed++;
                    }
                } else {
                    skipped++;
                }
            } else if (fs.existsSync(sourceAgent)) {
                if (!fs.existsSync(agentsDir)) {
                    fs.mkdirSync(agentsDir, { recursive: true });
                }
                fs.copyFileSync(sourceAgent, agentDest);
                installed++;
            }

            // Clean up legacy workflow file if agent is now installed
            const legacyWorkflow = path.join(githubDir, 'zotero-research-workflow.md');
            if (fs.existsSync(legacyWorkflow) && fs.existsSync(agentDest)) {
                const content = fs.readFileSync(legacyWorkflow, 'utf-8');
                if (content.includes('Zotero + PubMed MCP')) {
                    fs.unlinkSync(legacyWorkflow);
                    console.log('Removed legacy zotero-research-workflow.md (replaced by research.agent.md)');
                }
            }

            // Show result
            if (installed > 0) {
                vscode.window.showInformationMessage(
                    `✅ Installed/updated ${installed} Copilot file(s).${skipped > 0 ? ` ${skipped} file(s) preserved.` : ''}`
                );
            } else if (skipped > 0) {
                vscode.window.showInformationMessage(
                    `ℹ️ All ${skipped} file(s) preserved. Your custom configurations were not modified.`
                );
            } else {
                vscode.window.showInformationMessage('No files to install.');
            }
        })
    );
}

/**
 * Run setup wizard - handles all setup in one go
 */
async function runSetupWizard(): Promise<void> {
    const progress = await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Zotero MCP Setup',
            cancellable: false
        },
        async (progress) => {
            // Step 1: Check/setup Python
            progress.report({ message: 'Setting up Python environment...', increment: 0 });

            const pythonPath = await ensurePythonEnvironment();
            if (!pythonPath) {
                return false;
            }
            resolvedPythonPath = pythonPath;
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);
            progress.report({ message: 'Python OK ✓', increment: 33 });

            // Step 2: Ensure packages are installed
            progress.report({ message: 'Checking Python packages...', increment: 0 });
            const packagesOk = await ensurePackagesInstalled();
            if (!packagesOk) {
                vscode.window.showErrorMessage('Failed to install Python packages. Check the output panel.');
                return false;
            }
            await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);
            progress.report({ message: 'Packages OK ✓', increment: 33 });

            // Step 3: Check Zotero
            progress.report({ message: 'Checking Zotero connection...', increment: 34 });
            const zoteroOk = await checkAndUpdateZoteroStatus();

            if (!zoteroOk) {
                const choice = await vscode.window.showWarningMessage(
                    'Zotero is not running. Start Zotero to enable full functionality.',
                    'Download Zotero', 'Continue Anyway'
                );
                if (choice === 'Download Zotero') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.zotero.org/download/'));
                }
            }

            return true;
        }
    );

    if (progress) {
        // Re-initialize MCP provider if needed
        if (!mcpProvider && resolvedPythonPath) {
            mcpProvider = new ZoteroMcpServerProvider(resolvedPythonPath);
            const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
                'zotero-mcp.servers',
                mcpProvider
            );
            extensionContext.subscriptions.push(providerDisposable);
        }

        // Refresh MCP provider
        mcpProvider?.refresh();

        statusBar.setStatus('ready', 'Zotero MCP: Ready');

        vscode.window.showInformationMessage(
            '🎉 Zotero MCP is ready! Try asking Copilot to search PubMed.',
            'Open Copilot Chat'
        ).then(choice => {
            if (choice === 'Open Copilot Chat') {
                vscode.commands.executeCommand('workbench.action.chat.open');
            }
        });
    }
}

/**
 * Check if Zotero is accessible
 */
async function checkZoteroConnection(): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const host = config.get<string>('zoteroHost', 'localhost');
    const port = config.get<number>('zoteroPort', 23119);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
        const response = await fetch(`http://${host}:${port}/connector/ping`, {
            signal: controller.signal,
        });
        const text = await response.text();
        const ok = text.includes('Zotero is running');
        if (!ok) {
            console.warn(`Zotero ping responded but unexpected body: ${text.substring(0, 200)}`);
        }
        return ok;
    } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.warn(`Zotero connection check failed (${host}:${port}): ${msg}`);
        return false;
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Get extension status information
 */
async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const isUvManaged = uvPython.isReady();

    return {
        pythonPath: resolvedPythonPath || 'Not configured',
        pythonVersion: isUvManaged
            ? await uvPython.getPythonVersion() || 'Unknown'
            : await pythonEnv.getPythonVersion() || 'Unknown',
        pythonType: isUvManaged ? 'uv-managed (self-contained)' : 'System',
        packagesInstalled: isUvManaged ? true : await pythonEnv.checkPackages(),
        zoteroConnected: await checkZoteroConnection(),
        zoteroHost: config.get<string>('zoteroHost', 'localhost'),
        zoteroPort: config.get<number>('zoteroPort', 23119),
        enabledServers: {
            zoteroKeeper: config.get<boolean>('enableZoteroKeeper', true),
            pubmedSearch: config.get<boolean>('enablePubmedSearch', true),
        }
    };
}

interface ExtensionStatus {
    pythonPath: string;
    pythonVersion: string;
    pythonType: string;
    packagesInstalled: boolean;
    zoteroConnected: boolean;
    zoteroHost: string;
    zoteroPort: number;
    enabledServers: {
        zoteroKeeper: boolean;
        pubmedSearch: boolean;
    };
}

/**
 * Generate status webview HTML
 */
function getStatusWebviewContent(status: ExtensionStatus): string {
    const checkmark = '✅';
    const cross = '❌';

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zotero MCP Status</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        h1 { color: var(--vscode-titleBar-activeForeground); }
        .section {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .section h2 {
            margin-top: 0;
            font-size: 14px;
            color: var(--vscode-descriptionForeground);
        }
        .item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }
        .status { font-weight: bold; }
        .ok { color: #4caf50; }
        .error { color: #f44336; }
        .info { color: #2196f3; }
    </style>
</head>
<body>
    <h1>🔬 Zotero + PubMed MCP Status</h1>

    <div class="section">
        <h2>Python Environment</h2>
        <div class="item">
            <span>Type:</span>
            <span class="info">${status.pythonType}</span>
        </div>
        <div class="item">
            <span>Python Path:</span>
            <span style="font-size: 12px; word-break: break-all;">${status.pythonPath}</span>
        </div>
        <div class="item">
            <span>Python Version:</span>
            <span>${status.pythonVersion}</span>
        </div>
        <div class="item">
            <span>Packages Installed:</span>
            <span class="status ${status.packagesInstalled ? 'ok' : 'error'}">
                ${status.packagesInstalled ? checkmark : cross}
            </span>
        </div>
    </div>

    <div class="section">
        <h2>Zotero Connection</h2>
        <div class="item">
            <span>Host:</span>
            <span>${status.zoteroHost}:${status.zoteroPort}</span>
        </div>
        <div class="item">
            <span>Connected:</span>
            <span class="status ${status.zoteroConnected ? 'ok' : 'error'}">
                ${status.zoteroConnected ? checkmark : cross}
            </span>
        </div>
    </div>

    <div class="section">
        <h2>MCP Servers</h2>
        <div class="item">
            <span>Zotero Keeper:</span>
            <span class="status ${status.enabledServers.zoteroKeeper ? 'ok' : 'error'}">
                ${status.enabledServers.zoteroKeeper ? 'Enabled' : 'Disabled'}
            </span>
        </div>
        <div class="item">
            <span>PubMed Search:</span>
            <span class="status ${status.enabledServers.pubmedSearch ? 'ok' : 'error'}">
                ${status.enabledServers.pubmedSearch ? 'Enabled' : 'Disabled'}
            </span>
        </div>
    </div>
</body>
</html>`;
}

/**
 * Extension deactivation
 */
export function deactivate(): void {
    console.log('Zotero MCP extension is deactivating...');
    statusBar?.dispose();
}
