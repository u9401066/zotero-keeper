/**
 * Status Bar Manager
 * 
 * Shows extension status in VS Code status bar.
 */

import * as vscode from 'vscode';

type StatusType = 'initializing' | 'installing' | 'ready' | 'warning' | 'error';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'zoteroMcp.showStatus';
        this.statusBarItem.show();
    }

    /**
     * Update status bar display
     */
    setStatus(type: StatusType, text: string): void {
        this.statusBarItem.text = this.getIcon(type) + ' ' + text;
        this.statusBarItem.tooltip = this.getTooltip(type);
        this.statusBarItem.backgroundColor = this.getBackgroundColor(type);
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
        const apiInfo = details.slice(0, 3).join(' | ');
        
        switch (type) {
            case 'initializing':
                return 'Zotero MCP is initializing...';
            case 'installing':
                return 'Installing Python packages...';
            case 'ready':
                return `Zotero + PubMed MCP servers ready\n${apiInfo}\nClick for full status.`;
            case 'warning':
                return 'Zotero MCP has warnings. Click for details.';
            case 'error':
                return 'Zotero MCP error. Click for details.';
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
