/**
 * Status Bar Manager
 * 
 * Shows extension status in VS Code status bar with:
 * - Version number
 * - Quick menu access
 * - Statistics display
 * - API status overview
 */

import * as vscode from 'vscode';

type StatusType = 'initializing' | 'installing' | 'ready' | 'warning' | 'error';

// Statistics storage key
const STATS_KEY = 'zoteroMcp.statistics';

export interface UsageStatistics {
    articlesSearched: number;
    articlesImported: number;
    fulltextsAccessed: number;
    sessionsCount: number;
    lastUsed: string;
}

/**
 * Supported API information
 */
export interface ApiInfo {
    name: string;
    enabled: boolean;
    configured: boolean;
    description: string;
    rateLimit: string;
    settingsKey?: string;
}

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private context: vscode.ExtensionContext | undefined;
    private version: string = '0.5.10';

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'zoteroMcp.showQuickMenu';
        this.statusBarItem.show();
    }

    /**
     * Initialize with extension context for statistics storage
     */
    initialize(context: vscode.ExtensionContext): void {
        this.context = context;
        
        // Get version from package.json
        const packageJson = context.extension.packageJSON;
        this.version = packageJson.version || '0.5.2';
        
        // Register quick menu command
        context.subscriptions.push(
            vscode.commands.registerCommand('zoteroMcp.showQuickMenu', () => {
                this.showQuickMenu();
            })
        );
        
        // Register statistics commands
        context.subscriptions.push(
            vscode.commands.registerCommand('zoteroMcp.showStatistics', () => {
                this.showStatisticsPanel();
            })
        );
        
        context.subscriptions.push(
            vscode.commands.registerCommand('zoteroMcp.showApiStatus', () => {
                this.showApiStatusPanel();
            })
        );
        
        context.subscriptions.push(
            vscode.commands.registerCommand('zoteroMcp.resetStatistics', async () => {
                const confirm = await vscode.window.showWarningMessage(
                    'Reset all usage statistics?',
                    'Yes', 'No'
                );
                if (confirm === 'Yes') {
                    await this.resetStatistics();
                    vscode.window.showInformationMessage('Statistics reset.');
                }
            })
        );
        
        // Increment session count
        this.incrementStat('sessionsCount');
    }

    /**
     * Update status bar display with version
     */
    setStatus(type: StatusType, text: string): void {
        const icon = this.getIcon(type);
        const versionText = type === 'ready' ? ` v${this.version}` : '';
        this.statusBarItem.text = `${icon} ${text}${versionText}`;
        this.statusBarItem.tooltip = this.getTooltip(type);
        this.statusBarItem.backgroundColor = this.getBackgroundColor(type);
    }

    /**
     * Show quick access menu
     */
    async showQuickMenu(): Promise<void> {
        const stats = this.getStatistics();
        const apis = this.getSupportedApis();
        const enabledApis = apis.filter(a => a.enabled && a.configured).length;
        
        const items: vscode.QuickPickItem[] = [
            {
                label: '$(dashboard) Show Full Status',
                description: 'Open detailed status page',
                detail: 'View Python environment, Zotero connection, and more'
            },
            {
                label: '$(graph) Usage Statistics',
                description: `${stats.articlesSearched} searches, ${stats.articlesImported} imports`,
                detail: 'View detailed usage statistics'
            },
            {
                label: '$(globe) API Status',
                description: `${enabledApis}/${apis.length} APIs configured`,
                detail: 'View and manage connected APIs'
            },
            { label: '', kind: vscode.QuickPickItemKind.Separator },
            {
                label: '$(gear) Open Settings',
                description: 'Configure API keys and preferences'
            },
            {
                label: '$(wand) Setup Wizard',
                description: 'Run one-click setup'
            },
            {
                label: '$(plug) Check Zotero Connection',
                description: 'Verify Zotero is accessible'
            },
            { label: '', kind: vscode.QuickPickItemKind.Separator },
            {
                label: '$(book) Install Copilot Skills',
                description: 'Add research workflow guides to workspace'
            },
            {
                label: '$(refresh) Reinstall Python Environment',
                description: 'Fix Python environment issues'
            }
        ];
        
        const selection = await vscode.window.showQuickPick(items, {
            title: `Zotero + PubMed MCP v${this.version}`,
            placeHolder: 'Select an action...'
        });
        
        if (selection) {
            switch (selection.label) {
                case '$(dashboard) Show Full Status':
                    vscode.commands.executeCommand('zoteroMcp.showStatus');
                    break;
                case '$(graph) Usage Statistics':
                    this.showStatisticsPanel();
                    break;
                case '$(globe) API Status':
                    this.showApiStatusPanel();
                    break;
                case '$(gear) Open Settings':
                    vscode.commands.executeCommand('zoteroMcp.openSettings');
                    break;
                case '$(wand) Setup Wizard':
                    vscode.commands.executeCommand('zoteroMcp.setupWizard');
                    break;
                case '$(plug) Check Zotero Connection':
                    vscode.commands.executeCommand('zoteroMcp.checkConnection');
                    break;
                case '$(book) Install Copilot Skills':
                    vscode.commands.executeCommand('zoteroMcp.installSkills');
                    break;
                case '$(refresh) Reinstall Python Environment':
                    vscode.commands.executeCommand('zoteroMcp.reinstallPython');
                    break;
            }
        }
    }

    /**
     * Get all supported APIs with their status
     */
    getSupportedApis(): ApiInfo[] {
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        
        return [
            {
                name: 'PubMed / NCBI E-utilities',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: true, // Always available (email optional)
                description: 'Search 36M+ biomedical literature',
                rateLimit: config.get<string>('ncbiApiKey', '') ? '10 req/s' : '3 req/s',
                settingsKey: 'ncbiApiKey'
            },
            {
                name: 'Europe PMC',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: true, // Always available
                description: '33M+ articles, text mining, full-text',
                rateLimit: 'Fair use'
            },
            {
                name: 'CORE (Open Access)',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: !!config.get<string>('coreApiKey', ''),
                description: '200M+ open access papers',
                rateLimit: config.get<string>('coreApiKey', '') ? '5000 req/day' : '100 req/day',
                settingsKey: 'coreApiKey'
            },
            {
                name: 'Semantic Scholar',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: !!config.get<string>('semanticScholarApiKey', ''),
                description: 'AI-powered paper recommendations',
                rateLimit: 'Varies by plan',
                settingsKey: 'semanticScholarApiKey'
            },
            {
                name: 'PubChem',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: true,
                description: 'Chemical compound database',
                rateLimit: '5 req/s'
            },
            {
                name: 'NCBI Gene',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: true,
                description: 'Gene information database',
                rateLimit: config.get<string>('ncbiApiKey', '') ? '10 req/s' : '3 req/s'
            },
            {
                name: 'ClinVar',
                enabled: config.get<boolean>('enablePubmedSearch', true),
                configured: true,
                description: 'Clinical variant interpretations',
                rateLimit: config.get<string>('ncbiApiKey', '') ? '10 req/s' : '3 req/s'
            },
            {
                name: 'Zotero Local API',
                enabled: config.get<boolean>('enableZoteroKeeper', true),
                configured: true,
                description: 'Reference management',
                rateLimit: 'Local'
            }
        ];
    }

    /**
     * Show API status panel with management options
     */
    async showApiStatusPanel(): Promise<void> {
        const apis = this.getSupportedApis();
        
        const items: vscode.QuickPickItem[] = apis.map(api => ({
            label: `${api.configured ? '$(check)' : '$(circle-outline)'} ${api.name}`,
            description: api.rateLimit,
            detail: `${api.description}${!api.configured && api.settingsKey ? ' - Click to configure' : ''}`
        }));
        
        items.push(
            { label: '', kind: vscode.QuickPickItemKind.Separator },
            {
                label: '$(gear) Open API Settings',
                description: 'Configure all API keys'
            }
        );
        
        const selection = await vscode.window.showQuickPick(items, {
            title: 'Connected APIs',
            placeHolder: 'Select an API to configure...'
        });
        
        if (selection) {
            if (selection.label === '$(gear) Open API Settings') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp.ncbi');
            } else {
                // Find the API and open its settings
                const api = apis.find(a => selection.label.includes(a.name));
                if (api?.settingsKey) {
                    vscode.commands.executeCommand(
                        'workbench.action.openSettings', 
                        `zoteroMcp.${api.settingsKey}`
                    );
                } else {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp');
                }
            }
        }
    }

    /**
     * Show statistics panel
     */
    showStatisticsPanel(): void {
        const stats = this.getStatistics();
        const panel = vscode.window.createWebviewPanel(
            'zoteroMcpStats',
            'Zotero MCP Statistics',
            vscode.ViewColumn.One,
            {}
        );
        panel.webview.html = this.getStatisticsHtml(stats);
    }

    /**
     * Get statistics HTML content
     */
    private getStatisticsHtml(stats: UsageStatistics): string {
        const lastUsed = stats.lastUsed 
            ? new Date(stats.lastUsed).toLocaleDateString() 
            : 'Never';
        
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Usage Statistics</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        h1 { 
            color: var(--vscode-titleBar-activeForeground);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-number {
            font-size: 48px;
            font-weight: bold;
            color: var(--vscode-textLink-foreground);
        }
        .stat-label {
            font-size: 14px;
            color: var(--vscode-descriptionForeground);
            margin-top: 8px;
        }
        .info {
            background: var(--vscode-textBlockQuote-background);
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .version {
            color: var(--vscode-descriptionForeground);
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h1>📊 Usage Statistics <span class="version">v${this.version}</span></h1>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">${stats.articlesSearched}</div>
            <div class="stat-label">🔍 Searches Performed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.articlesImported}</div>
            <div class="stat-label">📥 Articles Imported</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.fulltextsAccessed}</div>
            <div class="stat-label">📄 Full-texts Accessed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.sessionsCount}</div>
            <div class="stat-label">🚀 Sessions</div>
        </div>
    </div>
    
    <div class="info">
        <strong>Last Activity:</strong> ${lastUsed}<br>
        <small>Statistics are stored locally and never shared.</small>
    </div>
</body>
</html>`;
    }

    /**
     * Get usage statistics
     */
    getStatistics(): UsageStatistics {
        if (!this.context) {
            return {
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: ''
            };
        }
        
        return this.context.globalState.get<UsageStatistics>(STATS_KEY, {
            articlesSearched: 0,
            articlesImported: 0,
            fulltextsAccessed: 0,
            sessionsCount: 0,
            lastUsed: ''
        });
    }

    /**
     * Increment a statistic
     */
    async incrementStat(key: keyof Omit<UsageStatistics, 'lastUsed'>, amount: number = 1): Promise<void> {
        if (!this.context) return;
        
        const stats = this.getStatistics();
        stats[key] = (stats[key] || 0) + amount;
        stats.lastUsed = new Date().toISOString();
        
        await this.context.globalState.update(STATS_KEY, stats);
    }

    /**
     * Reset statistics
     */
    async resetStatistics(): Promise<void> {
        if (!this.context) return;
        
        await this.context.globalState.update(STATS_KEY, {
            articlesSearched: 0,
            articlesImported: 0,
            fulltextsAccessed: 0,
            sessionsCount: 0,
            lastUsed: ''
        });
    }

    /**
     * Get detailed status including API configuration
     */
    getApiStatus(): { hasApiKeys: boolean; details: string[] } {
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const details: string[] = [];
        let hasApiKeys = false;

        // Check email (required)
        const email = config.get<string>('ncbiEmail', '');
        if (email) {
            details.push('✅ NCBI Email configured');
        } else {
            details.push('⚠️ NCBI Email not set (recommended)');
        }

        // Check optional API keys
        if (config.get<string>('ncbiApiKey', '')) {
            details.push('✅ NCBI API Key (10 req/s)');
            hasApiKeys = true;
        } else {
            details.push('ℹ️ NCBI API Key not set (3 req/s limit)');
        }

        if (config.get<string>('coreApiKey', '')) {
            details.push('✅ CORE API Key (5000 req/day)');
            hasApiKeys = true;
        } else {
            details.push('ℹ️ CORE API Key not set (100 req/day limit)');
        }

        if (config.get<string>('semanticScholarApiKey', '')) {
            details.push('✅ Semantic Scholar API Key');
            hasApiKeys = true;
        }

        // Check proxy
        const httpProxy = config.get<string>('httpProxy', '');
        const httpsProxy = config.get<string>('httpsProxy', '');
        if (httpProxy || httpsProxy) {
            details.push(`🌐 Proxy: ${httpProxy || httpsProxy}`);
        }

        return { hasApiKeys, details };
    }

    private getIcon(type: StatusType): string {
        switch (type) {
            case 'initializing':
                return '$(sync~spin)';
            case 'installing':
                return '$(sync~spin)';
            case 'ready':
                return '$(beaker)';
            case 'warning':
                return '$(warning)';
            case 'error':
                return '$(error)';
        }
    }

    private getTooltip(type: StatusType): string {
        const { details } = this.getApiStatus();
        const stats = this.getStatistics();
        const apiInfo = details.slice(0, 3).join(' | ');
        const statsInfo = `📊 ${stats.articlesSearched} searches | ${stats.articlesImported} imports`;
        
        switch (type) {
            case 'initializing':
                return 'Zotero MCP is initializing...';
            case 'installing':
                return 'Installing Python packages...';
            case 'ready':
                return `Zotero + PubMed MCP v${this.version} ready\n${apiInfo}\n${statsInfo}\n\nClick for menu`;
            case 'warning':
                return 'Zotero MCP has warnings. Click for menu.';
            case 'error':
                return 'Zotero MCP error. Click for menu.';
        }
    }

    private getBackgroundColor(type: StatusType): vscode.ThemeColor | undefined {
        switch (type) {
            case 'error':
                return new vscode.ThemeColor('statusBarItem.errorBackground');
            case 'warning':
                return new vscode.ThemeColor('statusBarItem.warningBackground');
            default:
                return undefined;
        }
    }

    /**
     * Dispose resources
     */
    dispose(): void {
        this.statusBarItem.dispose();
    }
}
