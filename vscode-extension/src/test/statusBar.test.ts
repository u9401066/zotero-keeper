import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import * as assert from 'assert';
import { StatusBarManager } from '../statusBar.js';
import { createMockContext, MockStatusBarItem, MockWorkspaceConfiguration } from './mock-vscode.js';
import * as fs from 'fs';
import * as path from 'path';

const shippedVersion: string = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '..', '..', 'package.json'), 'utf-8')
).version;

describe('StatusBarManager', () => {
    let manager: StatusBarManager;
    let item: MockStatusBarItem;

    const useConfig = (values: Record<string, unknown> = {}): void => {
        (vscode.workspace.getConfiguration as sinon.SinonStub).returns(new MockWorkspaceConfiguration(values));
    };

    beforeEach(() => {
        sinon.restore();
        (vscode.window.createStatusBarItem as sinon.SinonStub).resetHistory();
        (vscode.commands.registerCommand as sinon.SinonStub).resetHistory();
        useConfig();
        manager = new StatusBarManager();
        item = (vscode.window.createStatusBarItem as sinon.SinonStub).lastCall.returnValue;
    });

    afterEach(() => {
        manager.dispose();
    });

    describe('status text', () => {
        it('shows the packaged extension version only in the ready state', () => {
            const ctx = createMockContext();
            ctx.extension.packageJSON = { version: '1.2.3' };
            manager.initialize(ctx);

            manager.setStatus('ready', 'Zotero MCP: Ready');
            assert.ok(item.text.includes('v1.2.3'), item.text);

            manager.setStatus('error', 'Zotero MCP: Failed');
            assert.ok(!item.text.includes('v1.2.3'), item.text);
            assert.ok(item.backgroundColor, 'error state must use the error background');
        });

        it('does not claim a stale hardcoded version when package.json has none', () => {
            const ctx = createMockContext();
            ctx.extension.packageJSON = {};
            manager.initialize(ctx);
            manager.setStatus('ready', 'ready');
            assert.ok(!item.text.includes(`v${shippedVersion}`), item.text);
        assert.ok(item.text.includes('v0.0.0'), item.text);
        });
    });

    describe('commands', () => {
        it('registers each command once and counts the session', () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({ sessionsCount: 5, lastUsed: '' });
            manager.initialize(ctx);

            const names = (vscode.commands.registerCommand as sinon.SinonStub).getCalls().map(c => c.args[0]);
            assert.deepStrictEqual(names.sort(), [
                'zoteroMcp.resetStatistics',
                'zoteroMcp.showApiStatus',
                'zoteroMcp.showQuickMenu',
                'zoteroMcp.showStatistics',
            ]);
            assert.strictEqual(ctx.globalState.update.lastCall.args[1].sessionsCount, 6);
        });
    });

    describe('statistics', () => {
        it('returns zeros before initialization', () => {
            assert.deepStrictEqual(manager.getStatistics(), { sessionsCount: 0, lastUsed: '' });
        });

        it('tolerates legacy stored objects and partial state', () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({ articlesSearched: 42, lastUsed: '2025-01-01T00:00:00.000Z' });
            manager.initialize(ctx);
            const stats = manager.getStatistics();
            assert.strictEqual(stats.sessionsCount, 0);
            assert.strictEqual(stats.lastUsed, '2025-01-01T00:00:00.000Z');
        });

        it('increments by the requested amount and stamps lastUsed', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({ sessionsCount: 10, lastUsed: '' });
            manager.initialize(ctx);
            ctx.globalState.update.resetHistory();

            await manager.incrementStat('sessionsCount', 5);

            const saved = ctx.globalState.update.lastCall.args[1];
            assert.strictEqual(saved.sessionsCount, 15);
            assert.ok(!Number.isNaN(Date.parse(saved.lastUsed)));
        });

        it('resets to zero', async () => {
            const ctx = createMockContext();
            ctx.globalState.get.returns({ sessionsCount: 9, lastUsed: '2025-01-01' });
            manager.initialize(ctx);

            await manager.resetStatistics();

            assert.deepStrictEqual(ctx.globalState.update.lastCall.args[1], { sessionsCount: 0, lastUsed: '' });
        });
    });

    describe('getSupportedApis', () => {
        it('marks keyed APIs configured only when a key is present', () => {
            useConfig({ coreApiKey: '', semanticScholarApiKey: 's2' });
            const apis = manager.getSupportedApis();
            assert.strictEqual(apis.find(a => a.name === 'CORE (Open Access)')?.configured, false);
            assert.strictEqual(apis.find(a => a.name === 'Semantic Scholar')?.configured, true);
        });

        it('reports the PubMed rate limit according to the NCBI key', () => {
            useConfig({ ncbiApiKey: '' });
            assert.strictEqual(manager.getSupportedApis()[0].rateLimit, '3 req/s');
            useConfig({ ncbiApiKey: 'k' });
            assert.strictEqual(manager.getSupportedApis()[0].rateLimit, '10 req/s');
        });

        it('follows the server enable switches', () => {
            useConfig({ enablePubmedSearch: false, enableZoteroKeeper: true });
            const apis = manager.getSupportedApis();
            assert.ok(apis.filter(a => a.name !== 'Zotero Local API').every(a => !a.enabled));
            assert.strictEqual(apis.find(a => a.name === 'Zotero Local API')?.enabled, true);
        });
    });

    describe('getApiStatus', () => {
        it('flags a missing NCBI email and no keys', () => {
            const status = manager.getApiStatus();
            assert.strictEqual(status.hasApiKeys, false);
            assert.ok(status.details.some(d => d.includes('NCBI Email not set')));
        });

        it('lists configured keys', () => {
            useConfig({ ncbiEmail: 'a@b.c', ncbiApiKey: 'k', coreApiKey: 'c', openAlexApiKey: 'o' });
            const status = manager.getApiStatus();
            assert.strictEqual(status.hasApiKeys, true);
            for (const label of ['NCBI Email configured', 'NCBI API Key', 'CORE API Key', 'OpenAlex API Key']) {
                assert.ok(status.details.some(d => d.includes(label)), label);
            }
        });

        it('never shows proxy credentials', () => {
            useConfig({ httpsProxy: 'https://user:s3cret@proxy.example:8443' });
            const details = manager.getApiStatus().details.join('\n');
            assert.ok(details.includes('proxy.example:8443'));
            assert.ok(!details.includes('s3cret'), details);
            assert.ok(!details.includes('user:'), details);
        });

        it('never puts API keys into the tooltip', () => {
            useConfig({ ncbiApiKey: 'SECRET-KEY-123' });
            manager.setStatus('ready', 'ready');
            assert.ok(!String(item.tooltip).includes('SECRET-KEY-123'));
        });
    });
});
