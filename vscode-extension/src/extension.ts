/**
 * Zotero + PubMed MCP Extension
 * 
 * Provides AI-powered research assistant capabilities by integrating
 * Zotero reference management and PubMed literature search with GitHub Copilot.
 */

import * as vscode from 'vscode';
import { PythonEnvironment } from './pythonEnvironment';
import { ZoteroMcpServerProvider } from './mcpProvider';
import { StatusBarManager } from './statusBar';

let pythonEnv: PythonEnvironment;
let mcpProvider: ZoteroMcpServerProvider;
let statusBar: StatusBarManager;
let extensionContext: vscode.ExtensionContext;

// Context keys for walkthrough completion tracking
const CONTEXT_PYTHON_READY = 'zoteroMcp.pythonReady';
const CONTEXT_PACKAGES_READY = 'zoteroMcp.packagesReady';
const CONTEXT_ZOTERO_CONNECTED = 'zoteroMcp.zoteroConnected';
const FIRST_ACTIVATION_KEY = 'zoteroMcp.firstActivation';

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Zotero MCP extension is activating...');
    extensionContext = context;

    // Initialize components
    pythonEnv = new PythonEnvironment(context);
    statusBar = new StatusBarManager();
    
    // Register commands first (so they're available even if setup fails)
    registerCommands(context);
    
    // Show initial status
    statusBar.setStatus('initializing', 'Zotero MCP: Initializing...');

    try {
        // Step 1: Ensure Python is available
        const pythonPath = await pythonEnv.ensurePython();
        if (!pythonPath) {
            statusBar.setStatus('error', 'Zotero MCP: Python not found');
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, false);
            showFirstTimeWalkthrough(context);
            return;
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);

        // Step 2: Check/install required packages
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const autoInstall = config.get<boolean>('autoInstallPackages', true);
        
        let packagesInstalled = await pythonEnv.checkPackages();
        
        if (!packagesInstalled) {
            if (autoInstall) {
                statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                packagesInstalled = await pythonEnv.installPackages();
                if (!packagesInstalled) {
                    statusBar.setStatus('error', 'Zotero MCP: Package install failed');
                    await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
                    showFirstTimeWalkthrough(context);
                    return;
                }
            } else {
                const choice = await vscode.window.showInformationMessage(
                    'Zotero MCP requires Python packages (zotero-keeper, pubmed-search-mcp). Install now?',
                    'Install', 'Later'
                );
                if (choice === 'Install') {
                    statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                    packagesInstalled = await pythonEnv.installPackages();
                }
                if (!packagesInstalled) {
                    statusBar.setStatus('warning', 'Zotero MCP: Packages not installed');
                    await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
                    showFirstTimeWalkthrough(context);
                    return;
                }
            }
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);

        // Step 3: Register MCP server provider
        mcpProvider = new ZoteroMcpServerProvider(pythonEnv);
        
        const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'zotero-mcp.servers',
            mcpProvider
        );
        context.subscriptions.push(providerDisposable);

        // Step 4: Check Zotero connection (non-blocking)
        checkAndUpdateZoteroStatus();

        // Step 5: Update status
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
                const choice = await vscode.window.showWarningMessage(
                    '❌ Cannot connect to Zotero. Make sure Zotero 7 is running.',
                    'Download Zotero', 'Open Settings'
                );
                if (choice === 'Download Zotero') {
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
            // Step 1: Check Python
            progress.report({ message: 'Checking Python...', increment: 0 });
            const pythonPath = await pythonEnv.ensurePython();
            if (!pythonPath) {
                vscode.window.showErrorMessage(
                    'Python 3.11+ not found. Please install Python first.',
                    'Download Python'
                ).then(choice => {
                    if (choice === 'Download Python') {
                        vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
                    }
                });
                return false;
            }
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);
            progress.report({ message: 'Python OK ✓', increment: 25 });

            // Step 2: Install packages
            progress.report({ message: 'Installing Python packages...', increment: 25 });
            const packagesOk = await pythonEnv.checkPackages() || await pythonEnv.installPackages();
            if (!packagesOk) {
                vscode.window.showErrorMessage('Failed to install Python packages. Check the output panel.');
                return false;
            }
            await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);
            progress.report({ message: 'Packages OK ✓', increment: 25 });

            // Step 3: Check Zotero
            progress.report({ message: 'Checking Zotero connection...', increment: 25 });
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
        // Refresh MCP provider
        mcpProvider?.refresh();
        
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
    
    try {
        const response = await fetch(`http://${host}:${port}/connector/ping`);
        const text = await response.text();
        return text.includes('Zotero is running');
    } catch {
        return false;
    }
}

/**
 * Get extension status information
 */
async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    
    return {
        pythonPath: pythonEnv.getPythonPath() || 'Not found',
        pythonVersion: await pythonEnv.getPythonVersion() || 'Unknown',
        packagesInstalled: await pythonEnv.checkPackages(),
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
    </style>
</head>
<body>
    <h1>🔬 Zotero + PubMed MCP Status</h1>
    
    <div class="section">
        <h2>Python Environment</h2>
        <div class="item">
            <span>Python Path:</span>
            <span>${status.pythonPath}</span>
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
