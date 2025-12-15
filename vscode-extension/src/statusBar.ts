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
        switch (type) {
            case 'initializing':
                return 'Zotero MCP is initializing...';
            case 'installing':
                return 'Installing Python packages...';
            case 'ready':
                return 'Zotero + PubMed MCP servers ready. Click for status.';
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
