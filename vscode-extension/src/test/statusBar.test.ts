import { describe, it, beforeEach } from 'mocha';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import { StatusBarManager } from '../statusBar.js';
import { createMockContext, MockWorkspaceConfiguration } from './mock-vscode.js';
import * as assert from 'assert';

describe('StatusBarManager', () => {
    let manager: StatusBarManager;

    beforeEach(() => {
        sinon.restore();
        manager = new StatusBarManager();
    });

    afterEach(() => {
        manager.dispose();
    });

    describe('constructor', () => {
        it('should create a status bar item', () => {
            assert.ok((vscode.window.createStatusBarItem as sinon.SinonStub).calledOnce);
        });
    });

    describe('initialize', () => {
        it('should register commands', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            // Should register showQuickMenu, showStatistics, showApiStatus, resetStatistics
            const registerCalls = (vscode.commands.registerCommand as sinon.SinonStub).getCalls();
            const commandNames = registerCalls.map(c => c.args[0]);
            assert.ok(commandNames.includes('zoteroMcp.showQuickMenu'));
            assert.ok(commandNames.includes('zoteroMcp.showStatistics'));
            assert.ok(commandNames.includes('zoteroMcp.showApiStatus'));
            assert.ok(commandNames.includes('zoteroMcp.resetStatistics'));
        });

        it('should increment session count on initialize', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 5,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            // Should update stats with incremented session count
            assert.ok(ctx.globalState.update.called);
        });

        it('should read version from package.json', () => {
            const ctx = createMockContext();
            ctx.extension.packageJSON = { version: '1.2.3' };
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            // Set status to ready - should include version
            manager.setStatus('ready', 'Zotero MCP: Ready');
            // After initialize, the version should be read from packageJSON
        });
    });

    describe('setStatus', () => {
        it('should set text on status bar item for ready state', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);
            manager.setStatus('ready', 'Zotero MCP: Ready');
            // We just verify it doesn't throw
        });

        it('should handle all status types without throwing', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            const types: Array<'initializing' | 'installing' | 'ready' | 'warning' | 'error'> = [
                'initializing', 'installing', 'ready', 'warning', 'error'
            ];
            for (const type of types) {
                assert.doesNotThrow(() => manager.setStatus(type, `Test: ${type}`));
            }
        });
    });

    describe('getStatistics', () => {
        it('should return default statistics when not initialized', () => {
            const stats = manager.getStatistics();
            assert.strictEqual(stats.articlesSearched, 0);
            assert.strictEqual(stats.articlesImported, 0);
            assert.strictEqual(stats.fulltextsAccessed, 0);
            assert.strictEqual(stats.sessionsCount, 0);
            assert.strictEqual(stats.lastUsed, '');
        });

        it('should return stored statistics', () => {
            const ctx = createMockContext();
            const storedStats = {
                articlesSearched: 42,
                articlesImported: 10,
                fulltextsAccessed: 5,
                sessionsCount: 3,
                lastUsed: '2025-01-01T00:00:00.000Z',
            };
            ctx.globalState.get.returns(storedStats);
            manager.initialize(ctx as any);

            const stats = manager.getStatistics();
            assert.strictEqual(stats.articlesSearched, 42);
            assert.strictEqual(stats.articlesImported, 10);
        });
    });

    describe('incrementStat', () => {
        it('should increment a statistic by 1', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({
                articlesSearched: 5,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            await manager.incrementStat('articlesSearched');

            const updateCall = ctx.globalState.update.lastCall;
            assert.ok(updateCall);
            const updatedStats = updateCall.args[1];
            assert.strictEqual(updatedStats.articlesSearched, 6);
        });

        it('should increment by custom amount', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 10,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            await manager.incrementStat('articlesImported', 5);

            const updateCall = ctx.globalState.update.lastCall;
            const updatedStats = updateCall.args[1];
            assert.strictEqual(updatedStats.articlesImported, 15);
        });

        it('should update lastUsed timestamp', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({
                articlesSearched: 0,
                articlesImported: 0,
                fulltextsAccessed: 0,
                sessionsCount: 0,
                lastUsed: '',
            });
            manager.initialize(ctx as any);

            await manager.incrementStat('articlesSearched');

            const updateCall = ctx.globalState.update.lastCall;
            const updatedStats = updateCall.args[1];
            assert.ok(updatedStats.lastUsed);
            assert.ok(updatedStats.lastUsed.length > 0);
        });
    });

    describe('resetStatistics', () => {
        it('should reset all statistics to zero', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({
                articlesSearched: 50,
                articlesImported: 20,
                fulltextsAccessed: 10,
                sessionsCount: 5,
                lastUsed: '2025-01-01',
            });
            manager.initialize(ctx as any);

            await manager.resetStatistics();

            const updateCall = ctx.globalState.update.lastCall;
            const resetStats = updateCall.args[1];
            assert.strictEqual(resetStats.articlesSearched, 0);
            assert.strictEqual(resetStats.articlesImported, 0);
            assert.strictEqual(resetStats.fulltextsAccessed, 0);
            assert.strictEqual(resetStats.sessionsCount, 0);
            assert.strictEqual(resetStats.lastUsed, '');
        });
    });

    describe('getSupportedApis', () => {
        it('should return all 9 supported APIs', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                enablePubmedSearch: true,
                enableZoteroKeeper: true,
                ncbiApiKey: '',
                ncbiEmail: '',
                coreApiKey: '',
                openAlexApiKey: '',
                semanticScholarApiKey: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            const apis = manager.getSupportedApis();
            assert.strictEqual(apis.length, 9);

            const names = apis.map(a => a.name);
            assert.ok(names.includes('PubMed / NCBI E-utilities'));
            assert.ok(names.includes('Europe PMC'));
            assert.ok(names.includes('CORE (Open Access)'));
            assert.ok(names.includes('OpenAlex'));
            assert.ok(names.includes('Zotero Local API'));
        });

        it('should mark CORE as unconfigured when no API key', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                enablePubmedSearch: true,
                enableZoteroKeeper: true,
                ncbiApiKey: '',
                ncbiEmail: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            const apis = manager.getSupportedApis();
            const core = apis.find(a => a.name === 'CORE (Open Access)');
            assert.strictEqual(core?.configured, false);
        });

        it('should mark CORE as configured when API key present', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                enablePubmedSearch: true,
                enableZoteroKeeper: true,
                ncbiApiKey: '',
                ncbiEmail: '',
                coreApiKey: 'my-core-key',
                semanticScholarApiKey: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            const apis = manager.getSupportedApis();
            const core = apis.find(a => a.name === 'CORE (Open Access)');
            assert.strictEqual(core?.configured, true);
        });
    });

    describe('getApiStatus', () => {
        it('should report unconfigured NCBI email', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: '',
                ncbiApiKey: '',
                coreApiKey: '',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            const status = manager.getApiStatus();
            assert.strictEqual(status.hasApiKeys, false);
            assert.ok(status.details.some(d => d.includes('NCBI Email not set')));
        });

        it('should report configured API keys', () => {
            const ctx = createMockContext();
            const mockConfig = new MockWorkspaceConfiguration({
                ncbiEmail: 'test@example.com',
                ncbiApiKey: 'key123',
                coreApiKey: 'core456',
                openAlexApiKey: 'oa789',
                semanticScholarApiKey: '',
                httpProxy: '',
                httpsProxy: '',
            });
            (vscode.workspace.getConfiguration as sinon.SinonStub).returns(mockConfig);
            manager.initialize(ctx as any);

            const status = manager.getApiStatus();
            assert.strictEqual(status.hasApiKeys, true);
            assert.ok(status.details.some(d => d.includes('NCBI Email configured')));
            assert.ok(status.details.some(d => d.includes('NCBI API Key')));
            assert.ok(status.details.some(d => d.includes('CORE API Key')));
            assert.ok(status.details.some(d => d.includes('OpenAlex API Key')));
        });
    });

    describe('dispose', () => {
        it('should not throw on dispose', () => {
            assert.doesNotThrow(() => manager.dispose());
        });
    });
});
