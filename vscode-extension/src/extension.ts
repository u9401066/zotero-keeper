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

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Zotero MCP extension is activating...');

    // Initialize components
    pythonEnv = new PythonEnvironment(context);
    statusBar = new StatusBarManager();
    
    // Show initial status
    statusBar.setStatus('initializing', 'Zotero MCP: Initializing...');

    try {
        // Step 1: Ensure Python is available
        const pythonPath = await pythonEnv.ensurePython();
        if (!pythonPath) {
            statusBar.setStatus('error', 'Zotero MCP: Python not found');
            vscode.window.showErrorMessage(
                'Zotero MCP: Python 3.11+ not found. Please install Python or set the path in settings.',
                'Open Settings'
            ).then(choice => {
                if (choice === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp.pythonPath');
                }
            });
            return;
        }

        // Step 2: Check/install required packages
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const autoInstall = config.get<boolean>('autoInstallPackages', true);
        
        const packagesInstalled = await pythonEnv.checkPackages();
        
        if (!packagesInstalled) {
            if (autoInstall) {
                statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                const installed = await pythonEnv.installPackages();
                if (!installed) {
                    statusBar.setStatus('error', 'Zotero MCP: Package install failed');
                    return;
                }
            } else {
                const choice = await vscode.window.showInformationMessage(
                    'Zotero MCP requires Python packages (zotero-keeper, pubmed-search-mcp). Install now?',
                    'Install', 'Later'
                );
                if (choice === 'Install') {
                    statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                    await pythonEnv.installPackages();
                } else {
                    statusBar.setStatus('warning', 'Zotero MCP: Packages not installed');
                    return;
                }
            }
        }

        // Step 3: Register MCP server provider
        mcpProvider = new ZoteroMcpServerProvider(pythonEnv);
        
        const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'zotero-mcp.servers',
            mcpProvider
        );
        context.subscriptions.push(providerDisposable);

        // Step 4: Register commands
        registerCommands(context);

        // Step 5: Update status
        statusBar.setStatus('ready', 'Zotero MCP: Ready');
        
        console.log('Zotero MCP extension activated successfully');

    } catch (error) {
        console.error('Zotero MCP activation error:', error);
        statusBar.setStatus('error', 'Zotero MCP: Activation failed');
        vscode.window.showErrorMessage(`Zotero MCP activation failed: ${error}`);
    }
}

/**
 * Register extension commands
 */
function registerCommands(context: vscode.ExtensionContext): void {
    // Check Zotero connection
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.checkConnection', async () => {
            const connected = await checkZoteroConnection();
            if (connected) {
                vscode.window.showInformationMessage('✅ Zotero is running and accessible!');
            } else {
                vscode.window.showWarningMessage(
                    '❌ Cannot connect to Zotero. Make sure Zotero 7 is running.',
                    'Open Zotero Settings'
                ).then(choice => {
                    if (choice === 'Open Zotero Settings') {
                        vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp.zotero');
                    }
                });
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
                vscode.window.showInformationMessage('✅ Python packages installed successfully!');
                // Refresh MCP servers
                mcpProvider.refresh();
            } else {
                statusBar.setStatus('error', 'Zotero MCP: Install failed');
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
