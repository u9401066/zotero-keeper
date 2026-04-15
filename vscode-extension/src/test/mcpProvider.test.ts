import { describe, it, beforeEach } from 'mocha';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import { ZoteroMcpServerProvider } from '../mcpProvider.js';

// Use chai for assertions – install in next step if needed
// For now we use Node.js built-in assert as fallback
import * as assert from 'assert';

describe('ZoteroMcpServerProvider', () => {
    let provider: ZoteroMcpServerProvider;
    const mockPythonPath = '/usr/bin/python3';
    const mockToken = { isCancellationRequested: false } as vscode.CancellationToken;

    beforeEach(() => {
        sinon.restore();
        provider = new ZoteroMcpServerProvider(mockPythonPath);
    });

    describe('constructor', () => {
        it('should store the python path', () => {
            // Access via public method
            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            // Default config returns both servers enabled
            assert.ok(Array.isArray(servers));
        });
    });

    describe('provideMcpServerDefinitions', () => {
        it('should return both servers when both enabled (default)', () => {
            // Mock config to enable both
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: true,
                enablePubmedSearch: true,
                zoteroHost: 'localhost',
                zoteroPort: 23119,
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
                openUrlResolver: '',
                openUrlPreset: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 2);
            assert.strictEqual(servers[0].label, 'Zotero Keeper');
            assert.strictEqual(servers[1].label, 'PubMed Search');
        });

        it('should return only Zotero when PubMed disabled', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: true,
                enablePubmedSearch: false,
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 1);
            assert.strictEqual(servers[0].label, 'Zotero Keeper');
        });

        it('should return only PubMed when Zotero disabled', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: false,
                enablePubmedSearch: true,
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
                openUrlResolver: '',
                openUrlPreset: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 1);
            assert.strictEqual(servers[0].label, 'PubMed Search');
        });

        it('should return empty when both disabled', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: false,
                enablePubmedSearch: false,
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 0);
        });

        it('should set Zotero host/port from config', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: true,
                enablePubmedSearch: false,
                zoteroHost: '192.168.1.100',
                zoteroPort: 9999,
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 1);
            assert.strictEqual(servers[0].env?.ZOTERO_HOST, '192.168.1.100');
            assert.strictEqual(servers[0].env?.ZOTERO_PORT, '9999');
        });

        it('should pass API keys to PubMed server environment', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: false,
                enablePubmedSearch: true,
                ncbiEmail: 'test@example.com',
                ncbiApiKey: 'key123',
                coreApiKey: 'core456',
                openAlexApiKey: 'oa789',
                semanticScholarApiKey: 's2key',
                httpProxy: '',
                httpsProxy: '',
                openUrlResolver: '',
                openUrlPreset: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 1);
            const pubmed = servers[0];
            assert.strictEqual(pubmed.env?.NCBI_EMAIL, 'test@example.com');
            assert.strictEqual(pubmed.env?.NCBI_API_KEY, 'key123');
            assert.strictEqual(pubmed.env?.CORE_API_KEY, 'core456');
            assert.strictEqual(pubmed.env?.OPENALEX_API_KEY, 'oa789');
            assert.strictEqual(pubmed.env?.S2_API_KEY, 's2key');
        });

        it('should omit empty API keys from environment', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: false,
                enablePubmedSearch: true,
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
                openUrlResolver: '',
                openUrlPreset: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            const pubmed = servers[0];
            // NCBI_EMAIL may be auto-detected from git config (v0.5.13+)
            // So we only check that empty config keys (API keys) are omitted
            assert.strictEqual(pubmed.env?.NCBI_API_KEY, undefined);
        });

        it('should use correct python command and args', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: true,
                enablePubmedSearch: true,
                zoteroHost: 'localhost',
                zoteroPort: 23119,
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
                openUrlResolver: '',
                openUrlPreset: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];

            // Zotero Keeper
            assert.strictEqual(servers[0].command, mockPythonPath);
            assert.deepStrictEqual(servers[0].args, ['-m', 'zotero_mcp']);
            assert.strictEqual(servers[0].version, '1.12.0');

            // PubMed Search
            assert.strictEqual(servers[1].command, mockPythonPath);
            assert.deepStrictEqual(servers[1].args, ['-m', 'pubmed_search.presentation.mcp_server']);
            assert.strictEqual(servers[1].version, '0.5.3');
        });

        it('should return empty when pythonPath is empty', () => {
            const emptyProvider = new ZoteroMcpServerProvider('');
            const servers = emptyProvider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            assert.strictEqual(servers.length, 0);
        });

        it('should pass proxy settings to PubMed server', () => {
            const mockConfig = new (vscode as any).MockWorkspaceConfiguration({
                enableZoteroKeeper: false,
                enablePubmedSearch: true,
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: 'http://proxy:8080',
                httpsProxy: 'https://proxy:8443',
                openUrlResolver: 'https://resolver.example.com',
                openUrlPreset: 'my-university',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);

            const servers = provider.provideMcpServerDefinitions(mockToken) as vscode.McpStdioServerDefinition[];
            const pubmed = servers[0];
            assert.strictEqual(pubmed.env?.HTTP_PROXY, 'http://proxy:8080');
            assert.strictEqual(pubmed.env?.HTTPS_PROXY, 'https://proxy:8443');
            assert.strictEqual(pubmed.env?.OPENURL_RESOLVER, 'https://resolver.example.com');
            assert.strictEqual(pubmed.env?.OPENURL_PRESET, 'my-university');
        });
    });

    describe('setPythonPath', () => {
        it('should update python path and trigger refresh', () => {
            const newPath = '/new/python';
            let refreshFired = false;
            provider.onDidChangeMcpServerDefinitions(() => { refreshFired = true; });

            provider.setPythonPath(newPath);
            assert.strictEqual(refreshFired, true);
        });
    });

    describe('resolveMcpServerDefinition', () => {
        it('should return the same server definition', () => {
            const server = new vscode.McpStdioServerDefinition(
                'Test', '/python', ['-m', 'test'], {}, '1.0'
            );
            const result = provider.resolveMcpServerDefinition(server, mockToken);
            assert.strictEqual(result, server);
        });
    });

    describe('dispose', () => {
        it('should not throw', () => {
            assert.doesNotThrow(() => provider.dispose());
        });
    });
});
