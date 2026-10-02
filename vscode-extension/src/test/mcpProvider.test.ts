import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import childProcess from 'child_process';
import { ZoteroMcpServerProvider } from '../mcpProvider.js';
import { resetGitEmailCache } from '../mcpServerConfig.js';
import { MockWorkspaceConfiguration, workspace as mockWorkspace } from './mock-vscode.js';
import {
    PUBMED_SEARCH_ENTRYPOINT,
    PUBMED_SEARCH_VERSION,
    PUBMED_WORKSPACE_DIR_ENV,
} from '../pubmedSearchPackage.js';
import { ZOTERO_KEEPER_VERSION } from '../zoteroKeeperPackage.js';

describe('ZoteroMcpServerProvider', () => {
    const python = '/usr/bin/python3';
    const token = { isCancellationRequested: false } as vscode.CancellationToken;
    let provider: ZoteroMcpServerProvider;

    const useConfig = (values: Record<string, unknown>): void => {
        (vscode.workspace.getConfiguration as sinon.SinonStub).returns(new MockWorkspaceConfiguration(values));
    };
    const provide = (): vscode.McpStdioServerDefinition[] =>
        provider.provideMcpServerDefinitions(token) as vscode.McpStdioServerDefinition[];

    beforeEach(() => {
        sinon.restore();
        resetGitEmailCache();
        // No developer's global git identity may leak into assertions.
        sinon.stub(childProcess, 'execFileSync').throws(new Error('git unavailable'));
        provider = new ZoteroMcpServerProvider(python);
        mockWorkspace.workspaceFolders = undefined;
    });

    afterEach(() => {
        sinon.restore();
        resetGitEmailCache();
        mockWorkspace.workspaceFolders = undefined;
    });

    it('provides both servers with the pinned versions, in a stable order', () => {
        useConfig({});
        const [keeper, pubmed] = provide();

        assert.strictEqual(keeper.label, 'Zotero Keeper');
        assert.strictEqual(keeper.command, python);
        assert.deepStrictEqual(keeper.args, ['-m', 'zotero_mcp']);
        assert.strictEqual(keeper.version, ZOTERO_KEEPER_VERSION);
        assert.deepStrictEqual(keeper.env, { ZOTERO_HOST: 'localhost', ZOTERO_PORT: '23119' });

        assert.strictEqual(pubmed.label, 'PubMed Search');
        assert.deepStrictEqual(pubmed.args, ['-m', PUBMED_SEARCH_ENTRYPOINT]);
        assert.strictEqual(pubmed.version, PUBMED_SEARCH_VERSION);
    });

    it('honours the per-server enable switches', () => {
        useConfig({ enableZoteroKeeper: true, enablePubmedSearch: false });
        assert.deepStrictEqual(provide().map(s => s.label), ['Zotero Keeper']);

        useConfig({ enableZoteroKeeper: false, enablePubmedSearch: true });
        assert.deepStrictEqual(provide().map(s => s.label), ['PubMed Search']);

        useConfig({ enableZoteroKeeper: false, enablePubmedSearch: false });
        assert.deepStrictEqual(provide(), []);
    });

    it('passes Zotero host/port and the PubMed environment through', () => {
        mockWorkspace.workspaceFolders = [{ uri: { fsPath: '/mock/workspace' } }];
        useConfig({
            zoteroHost: '192.168.1.100',
            zoteroPort: 9999,
            ncbiEmail: 'test@example.com',
            ncbiApiKey: 'key123',
            httpsProxy: 'https://proxy:8443',
        });
        const [keeper, pubmed] = provide();

        assert.strictEqual(keeper.env?.ZOTERO_HOST, '192.168.1.100');
        assert.strictEqual(keeper.env?.ZOTERO_PORT, '9999');
        assert.deepStrictEqual(pubmed.env, {
            NCBI_EMAIL: 'test@example.com',
            NCBI_API_KEY: 'key123',
            HTTPS_PROXY: 'https://proxy:8443',
            [PUBMED_WORKSPACE_DIR_ENV]: '/mock/workspace',
        });
    });

    it('provides nothing (and does not throw) while no interpreter is known', () => {
        useConfig({});
        assert.deepStrictEqual(
            new ZoteroMcpServerProvider('').provideMcpServerDefinitions(token),
            [],
        );
    });

    it('switches interpreter and notifies VS Code to re-read the definitions', () => {
        useConfig({});
        let notifications = 0;
        provider.onDidChangeMcpServerDefinitions(() => { notifications++; });

        provider.setPythonPath('/new/python');

        assert.strictEqual(notifications, 1);
        assert.ok(provide().every(server => server.command === '/new/python'));
    });
});
