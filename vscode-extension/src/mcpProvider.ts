/**
 * MCP Server Definition Provider
 *
 * Provides Zotero Keeper and PubMed Search MCP servers to VS Code.
 */

import * as vscode from 'vscode';
import { ZOTERO_KEEPER_VERSION } from './zoteroKeeperPackage.js';
import {
    PUBMED_SEARCH_ENTRYPOINT,
    PUBMED_SEARCH_VERSION,
} from './pubmedSearchPackage.js';
import { buildPubmedEnv, buildZoteroEnv, getPrimaryWorkspaceFolder } from './mcpServerConfig.js';

export class ZoteroMcpServerProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition>, vscode.Disposable {

    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;

    private pythonPath: string;

    constructor(pythonPath: string, _context?: vscode.ExtensionContext) {
        this.pythonPath = pythonPath;
    }

    /**
     * Update Python path (used when switching between system/embedded).
     * Cline configuration is synchronized by the extension activation/commands
     * so provider refreshes and external settings writes stay on one path.
     */
    setPythonPath(pythonPath: string): void {
        this.pythonPath = pythonPath;
        this.refresh();
    }

    /**
     * Provide available MCP servers
     */
    provideMcpServerDefinitions(
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        const servers: vscode.McpStdioServerDefinition[] = [];
        const config = vscode.workspace.getConfiguration('zoteroMcp');

        if (!this.pythonPath) {
            console.warn('ZoteroMcpProvider: Python path not available');
            return servers;
        }

        if (config.get<boolean>('enableZoteroKeeper', true)) {
            servers.push(
                new vscode.McpStdioServerDefinition(
                    'Zotero Keeper',
                    this.pythonPath,
                    ['-m', 'zotero_mcp'],
                    buildZoteroEnv(config),
                    ZOTERO_KEEPER_VERSION
                )
            );
        }

        if (config.get<boolean>('enablePubmedSearch', true)) {
            servers.push(
                new vscode.McpStdioServerDefinition(
                    'PubMed Search',
                    this.pythonPath,
                    ['-m', PUBMED_SEARCH_ENTRYPOINT],
                    buildPubmedEnv(config, getPrimaryWorkspaceFolder()),
                    PUBMED_SEARCH_VERSION
                )
            );
        }

        return servers;
    }

    /**
     * Resolve server before starting (nothing to customize: definitions are final).
     */
    resolveMcpServerDefinition(
        server: vscode.McpStdioServerDefinition,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition> {
        return server;
    }

    /**
     * Trigger server list refresh
     */
    refresh(): void {
        this._onDidChangeMcpServerDefinitions.fire();
    }

    /**
     * Dispose resources
     */
    dispose(): void {
        this._onDidChangeMcpServerDefinitions.dispose();
    }
}
