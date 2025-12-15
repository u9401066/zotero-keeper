/**
 * MCP Server Definition Provider
 * 
 * Provides Zotero Keeper and PubMed Search MCP servers to VS Code.
 */

import * as vscode from 'vscode';
import { PythonEnvironment } from './pythonEnvironment';

export class ZoteroMcpServerProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    
    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;

    constructor(private pythonEnv: PythonEnvironment) {}

    /**
     * Provide available MCP servers
     */
    provideMcpServerDefinitions(
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        const servers: vscode.McpStdioServerDefinition[] = [];
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const pythonPath = this.pythonEnv.getPythonPath();

        if (!pythonPath) {
            console.warn('ZoteroMcpProvider: Python path not available');
            return servers;
        }

        // Zotero Keeper MCP Server
        if (config.get<boolean>('enableZoteroKeeper', true)) {
            const zoteroHost = config.get<string>('zoteroHost', 'localhost');
            const zoteroPort = config.get<number>('zoteroPort', 23119);

            servers.push(
                new vscode.McpStdioServerDefinition(
                    'Zotero Keeper',
                    pythonPath,
                    ['-m', 'zotero_mcp'],
                    {
                        ZOTERO_HOST: zoteroHost,
                        ZOTERO_PORT: String(zoteroPort),
                    },
                    '1.8.2'
                )
            );
        }

        // PubMed Search MCP Server
        if (config.get<boolean>('enablePubmedSearch', true)) {
            const ncbiEmail = config.get<string>('ncbiEmail', '');
            
            const env: Record<string, string> = {};
            if (ncbiEmail) {
                env['NCBI_EMAIL'] = ncbiEmail;
            }

            servers.push(
                new vscode.McpStdioServerDefinition(
                    'PubMed Search',
                    pythonPath,
                    ['-m', 'pubmed_search.mcp'],
                    env,
                    '0.1.14'
                )
            );
        }

        console.log(`ZoteroMcpProvider: Providing ${servers.length} MCP servers`);
        return servers;
    }

    /**
     * Resolve server before starting (optional customization point)
     */
    resolveMcpServerDefinition(
        server: vscode.McpStdioServerDefinition,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition> {
        // Perform any last-minute configuration
        // For example, could check Zotero connection here
        console.log(`ZoteroMcpProvider: Resolving server "${server.label}"`);
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
