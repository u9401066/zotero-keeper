/**
 * Status Bar Manager
 * 
 * Shows extension status in VS Code status bar with hover tooltip.
 * Inspired by Git extension - minimal status bar with rich hover info.
 */

import * as vscode from 'vscode';

type StatusType = 'initializing' | 'installing' | 'ready' | 'warning' | 'error';

interface DetailedStatus {
    pythonReady: boolean;
    pythonPath?: string;
    pythonVersion?: string;
    packagesReady: boolean;
    zoteroConnected: boolean;
    zoteroHost?: string;
    zoteroPort?: number;
    mcpServersEnabled?: {
        zoteroKeeper: boolean;
        pubmedSearch: boolean;
    };
}

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private currentType: StatusType = 'initializing';
    private detailedStatus: DetailedStatus = {
        pythonReady: false,
        packagesReady: false,
        zoteroConnected: false,
    };

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'zoteroMcp.showQuickStatus';
        this.statusBarItem.show();
    }

    /**
     * Update status bar display
     */
    setStatus(type: StatusType, text: string): void {
        this.currentType = type;
        this.statusBarItem.text = this.getIcon(type) + ' ' + this.getShortText(type);
        this.updateTooltip();
        this.statusBarItem.backgroundColor = this.getBackgroundColor(type);
    }

    /**
     * Update detailed status for tooltip
     */
    updateDetailedStatus(status: Partial<DetailedStatus>): void {
        this.detailedStatus = { ...this.detailedStatus, ...status };
        this.updateTooltip();
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

    private getShortText(type: StatusType): string {
        switch (type) {
            case 'initializing':
                return 'Zotero MCP';
            case 'installing':
                return 'Zotero MCP';
            case 'ready':
                return 'Zotero MCP';
            case 'warning':
                return 'Zotero MCP';
            case 'error':
                return 'Zotero MCP';
        }
    }

    private updateTooltip(): void {
        const md = new vscode.MarkdownString('', true);
        md.isTrusted = true;
        md.supportThemeIcons = true;
        
        // Title
        md.appendMarkdown('### $(beaker) Zotero + PubMed MCP\n\n');
        
        // Status overview
        const statusIcon = this.currentType === 'ready' ? '$(check)' : 
                          this.currentType === 'error' ? '$(error)' :
                          this.currentType === 'warning' ? '$(warning)' : '$(sync~spin)';
        const statusText = this.currentType === 'ready' ? 'Ready' :
                          this.currentType === 'error' ? 'Error' :
                          this.currentType === 'warning' ? 'Warning' :
                          this.currentType === 'installing' ? 'Installing...' : 'Initializing...';
        md.appendMarkdown(`**Status:** ${statusIcon} ${statusText}\n\n`);
        
        md.appendMarkdown('---\n\n');
        
        // Python Environment
        const pyIcon = this.detailedStatus.pythonReady ? '$(check)' : '$(x)';
        md.appendMarkdown(`**Python:** ${pyIcon} `);
        if (this.detailedStatus.pythonReady) {
            md.appendMarkdown(`${this.detailedStatus.pythonVersion || 'Ready'}\n`);
        } else {
            md.appendMarkdown('Not configured\n');
        }
        
        // Packages
        const pkgIcon = this.detailedStatus.packagesReady ? '$(check)' : '$(x)';
        md.appendMarkdown(`**Packages:** ${pkgIcon} ${this.detailedStatus.packagesReady ? 'Installed' : 'Not installed'}\n`);
        
        // Zotero Connection
        const zotIcon = this.detailedStatus.zoteroConnected ? '$(check)' : '$(x)';
        const zotHost = this.detailedStatus.zoteroHost || 'localhost';
        const zotPort = this.detailedStatus.zoteroPort || 23119;
        md.appendMarkdown(`**Zotero:** ${zotIcon} ${this.detailedStatus.zoteroConnected ? 'Connected' : 'Not connected'}`);
        md.appendMarkdown(` *(${zotHost}:${zotPort})*\n`);
        
        md.appendMarkdown('\n---\n\n');
        
        // Quick actions
        md.appendMarkdown('$(gear) [Settings](command:zoteroMcp.openSettings) · ');
        md.appendMarkdown('$(refresh) [Check Connection](command:zoteroMcp.checkConnection) · ');
        md.appendMarkdown('$(info) [Full Status](command:zoteroMcp.showStatus)\n');
        
        this.statusBarItem.tooltip = md;
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
