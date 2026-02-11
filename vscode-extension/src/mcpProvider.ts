/**
 * MCP Server Definition Provider
 * 
 * Provides Zotero Keeper and PubMed Search MCP servers to VS Code.
 */

import * as vscode from 'vscode';

export class ZoteroMcpServerProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    
    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;

    private pythonPath: string;

    constructor(pythonPath: string) {
        this.pythonPath = pythonPath;
    }

    /**
     * Update Python path (used when switching between system/embedded)
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

        // Zotero Keeper MCP Server
        if (config.get<boolean>('enableZoteroKeeper', true)) {
            const zoteroHost = config.get<string>('zoteroHost', 'localhost');
            const zoteroPort = config.get<number>('zoteroPort', 23119);

            servers.push(
                new vscode.McpStdioServerDefinition(
                    'Zotero Keeper',
                    this.pythonPath,
                    ['-m', 'zotero_mcp'],
                    {
                        ZOTERO_HOST: zoteroHost,
                        ZOTERO_PORT: String(zoteroPort),
                    },
                    '1.11.0'
                )
            );
        }

        // PubMed Search MCP Server
        if (config.get<boolean>('enablePubmedSearch', true)) {
            const ncbiEmail = config.get<string>('ncbiEmail', '');
            const ncbiApiKey = config.get<string>('ncbiApiKey', '');
            const coreApiKey = config.get<string>('coreApiKey', '');
            const semanticScholarApiKey = config.get<string>('semanticScholarApiKey', '');
            const httpProxy = config.get<string>('httpProxy', '');
            const httpsProxy = config.get<string>('httpsProxy', '');
            const openUrlResolver = config.get<string>('openUrlResolver', '');
            const openUrlPreset = config.get<string>('openUrlPreset', '');
            
            const env: Record<string, string> = {};
            if (ncbiEmail) {
                env['NCBI_EMAIL'] = ncbiEmail;
            }
            if (ncbiApiKey) {
                env['NCBI_API_KEY'] = ncbiApiKey;
            }
            if (coreApiKey) {
                env['CORE_API_KEY'] = coreApiKey;
            }
            if (semanticScholarApiKey) {
                env['S2_API_KEY'] = semanticScholarApiKey;
            }
            if (httpProxy) {
                env['HTTP_PROXY'] = httpProxy;
            }
            if (httpsProxy) {
                env['HTTPS_PROXY'] = httpsProxy;
            }
            // OpenURL / Institutional Access
            if (openUrlPreset) {
                env['OPENURL_PRESET'] = openUrlPreset;
            }
            if (openUrlResolver) {
                env['OPENURL_RESOLVER'] = openUrlResolver;
            }

            servers.push(
                new vscode.McpStdioServerDefinition(
                    'PubMed Search',
                    this.pythonPath,
                    ['-m', 'pubmed_search.presentation.mcp_server'],
                    env,
                    '0.3.8'
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
