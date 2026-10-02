/**
 * Unit tests for Cline MCP configuration manager
 */

import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import fileSystem from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import type { SinonStub } from 'sinon';
import {
    installClineMcpServers,
    removeClineMcpServers,
    isClineInstalled,
} from '../clineMcpConfig.js';
import { MockWorkspaceConfiguration } from './mock-vscode.js';

// Minimal mock of ExtensionContext
function createMockContext(globalStoragePath: string): vscode.ExtensionContext {
    return {
        globalStorageUri: { fsPath: globalStoragePath },
    } as vscode.ExtensionContext;
}

describe('clineMcpConfig', () => {
    let tmpDir: string;
    let mockContext: vscode.ExtensionContext;
    let clineSettingsPath: string;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'zotero-mcp-test-'));
        mockContext = createMockContext(path.join(tmpDir, 'globalStorage', 'u9401066.vscode-zotero-mcp'));
        clineSettingsPath = path.join(tmpDir, 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json');
        (vscode.extensions.getExtension as SinonStub).resetBehavior();
        (vscode.extensions.getExtension as SinonStub).returns(undefined);
        (vscode.workspace.getConfiguration as SinonStub).returns(new MockWorkspaceConfiguration({}));
    });

    afterEach(() => {
        sinon.restore();
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    describe('isClineInstalled', () => {
        it('should return true when Cline global storage exists', () => {
            const clineGlobalStorage = path.join(tmpDir, 'globalStorage', 'saoudrizwan.claude-dev');
            fs.mkdirSync(clineGlobalStorage, { recursive: true });
            assert.strictEqual(isClineInstalled(mockContext), true);
        });

        it('should return false when Cline global storage does not exist', () => {
            assert.strictEqual(isClineInstalled(mockContext), false);
        });

        it('should return true when Cline extension is installed but storage is absent', () => {
            (vscode.extensions.getExtension as SinonStub).withArgs('saoudrizwan.claude-dev').returns({ id: 'saoudrizwan.claude-dev' });
            assert.strictEqual(isClineInstalled(mockContext), true);
        });
    });

    describe('installClineMcpServers', () => {
        it('should return false when Cline global storage does not exist', () => {
            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, false);
            assert.strictEqual(fs.existsSync(clineSettingsPath), false);
        });

        it('should create settings when Cline extension exists but storage is absent', () => {
            (vscode.extensions.getExtension as SinonStub).withArgs('saoudrizwan.claude-dev').returns({ id: 'saoudrizwan.claude-dev' });

            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, true);
            assert.strictEqual(fs.existsSync(clineSettingsPath), true);
        });

        it('should create cline_mcp_settings.json with both servers', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });

            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, true);
            assert.strictEqual(fs.existsSync(clineSettingsPath), true);

            const settings = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.ok(settings.mcpServers['zotero-keeper']);
            assert.ok(settings.mcpServers['pubmed-search-mcp']);
            assert.strictEqual(settings.mcpServers['zotero-keeper'].command, '/usr/bin/python3');
            assert.deepStrictEqual(settings.mcpServers['zotero-keeper'].args, ['-m', 'zotero_mcp']);
            assert.deepStrictEqual(settings.mcpServers['pubmed-search-mcp'].args, ['-m', 'pubmed_search.presentation.mcp_server']);
        });

        it('should update existing settings without overwriting other servers', () => {
            // Pre-populate with another server
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, JSON.stringify({
                mcpServers: {
                    'other-server': { command: 'node', args: ['server.js'] },
                },
            }, null, 2));

            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, true);

            const settings = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.ok(settings.mcpServers['other-server']);
            assert.ok(settings.mcpServers['zotero-keeper']);
        });

        it('should back up invalid settings before replacing them', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, '{ invalid json', 'utf-8');

            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, true);

            const backupFiles = fs.readdirSync(path.dirname(clineSettingsPath))
                .filter(name => name.startsWith('cline_mcp_settings.json.invalid.') && name.endsWith('.bak'));
            assert.strictEqual(backupFiles.length, 1);
            assert.strictEqual(fs.readFileSync(path.join(path.dirname(clineSettingsPath), backupFiles[0]), 'utf-8'), '{ invalid json');
        });

        it('should preserve Cline-local disabled and alwaysAllow settings when updating managed servers', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, JSON.stringify({
                mcpServers: {
                    'zotero-keeper': {
                        command: '/old/python',
                        args: ['-m', 'zotero_mcp'],
                        env: {
                            ZOTERO_HOST: 'localhost',
                            ZOTERO_PORT: '23119',
                        },
                        disabled: true,
                        alwaysAllow: ['zotero_search'],
                    },
                    'pubmed-search-mcp': {
                        command: '/old/python',
                        args: ['-m', 'pubmed_search.presentation.mcp_server'],
                        disabled: true,
                        alwaysAllow: ['search_articles'],
                    },
                },
            }, null, 2));

            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            assert.strictEqual(updated, true);

            const settings = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.strictEqual(settings.mcpServers['zotero-keeper'].command, '/usr/bin/python3');
            assert.strictEqual(settings.mcpServers['pubmed-search-mcp'].command, '/usr/bin/python3');
            assert.strictEqual(settings.mcpServers['zotero-keeper'].disabled, true);
            assert.strictEqual(settings.mcpServers['pubmed-search-mcp'].disabled, true);
            assert.deepStrictEqual(settings.mcpServers['zotero-keeper'].alwaysAllow, ['zotero_search']);
            assert.deepStrictEqual(settings.mcpServers['pubmed-search-mcp'].alwaysAllow, ['search_articles']);
        });

        it('should return false when no changes are needed (idempotent)', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });

            // First install
            installClineMcpServers(mockContext, '/usr/bin/python3');
            const settingsAfterFirst = fs.readFileSync(clineSettingsPath, 'utf-8');
            // Second install with same path
            const updated = installClineMcpServers(mockContext, '/usr/bin/python3');
            const settingsAfterSecond = fs.readFileSync(clineSettingsPath, 'utf-8');
            assert.strictEqual(updated, false, `Expected false but got true. First:\n${settingsAfterFirst}\nSecond:\n${settingsAfterSecond}`);
        });
    });

    describe('removeClineMcpServers', () => {
        it('should remove managed servers while preserving others', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, JSON.stringify({
                mcpServers: {
                    'zotero-keeper': { command: '/usr/bin/python3', args: ['-m', 'zotero_mcp'] },
                    'other-server': { command: 'node', args: ['server.js'] },
                },
            }, null, 2));

            const updated = removeClineMcpServers(mockContext);
            assert.strictEqual(updated, true);

            const settings = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.strictEqual(settings.mcpServers['zotero-keeper'], undefined);
            assert.ok(settings.mcpServers['other-server']);
        });

        it('should return false when no managed servers exist', () => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, JSON.stringify({
                mcpServers: {
                    'other-server': { command: 'node', args: ['server.js'] },
                },
            }, null, 2));

            const updated = removeClineMcpServers(mockContext);
            assert.strictEqual(updated, false);
        });
    });

    describe('hostile or unusual settings files', () => {
        const backups = (): string[] => fs.readdirSync(path.dirname(clineSettingsPath)).filter(n => n.endsWith('.bak'));
        const seed = (content: string): void => {
            fs.mkdirSync(path.dirname(clineSettingsPath), { recursive: true });
            fs.writeFileSync(clineSettingsPath, content, 'utf-8');
        };

        for (const [label, content] of [
            ['a JSON array', '[]'],
            ['JSON null', 'null'],
            ['a bare string', '"hello"'],
            ['an empty file', ''],
            ['JSON with comments', '{ // my servers\n "mcpServers": {} }'],
        ] as const) {
            it(`backs up ${label} and still installs the managed servers`, () => {
                seed(content);
                assert.strictEqual(installClineMcpServers(mockContext, '/usr/bin/python3'), true);

                const written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
                assert.ok(written.mcpServers['zotero-keeper']);
                assert.strictEqual(backups().length, 1);
                assert.strictEqual(fs.readFileSync(path.join(path.dirname(clineSettingsPath), backups()[0]), 'utf-8'), content);
            });
        }

        it('reads a UTF-8 BOM file (Windows editors) without discarding the user\'s other servers', () => {
            seed('\uFEFF' + JSON.stringify({ mcpServers: { mine: { command: 'node', args: ['x.js'] } } }));
            assert.strictEqual(installClineMcpServers(mockContext, '/usr/bin/python3'), true);

            const written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.deepStrictEqual(written.mcpServers.mine, { command: 'node', args: ['x.js'] });
            assert.strictEqual(backups().length, 0);
        });

        it('keeps unknown top-level keys and repairs a non-object mcpServers', () => {
            seed(JSON.stringify({ theme: 'dark', mcpServers: [] }));
            installClineMcpServers(mockContext, '/usr/bin/python3');

            const written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.strictEqual(written.theme, 'dark');
            assert.ok(written.mcpServers['zotero-keeper']);
        });

        it('never touches a user-owned server that merely reuses a managed key', () => {
            const mine = { command: 'node', args: ['my-zotero.js'], env: { A: '1' } };
            seed(JSON.stringify({ mcpServers: { 'zotero-keeper': mine } }));

            installClineMcpServers(mockContext, '/usr/bin/python3');
            let written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.deepStrictEqual(written.mcpServers['zotero-keeper'], mine);

            (vscode.workspace.getConfiguration as SinonStub).returns(new MockWorkspaceConfiguration({ enableZoteroKeeper: false }));
            installClineMcpServers(mockContext, '/usr/bin/python3');
            written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.deepStrictEqual(written.mcpServers['zotero-keeper'], mine);
        });

        it('removes its own entries when a server is disabled, leaving the other one', () => {
            seed(JSON.stringify({ mcpServers: {} }));
            installClineMcpServers(mockContext, '/usr/bin/python3');
            (vscode.workspace.getConfiguration as SinonStub).returns(new MockWorkspaceConfiguration({ enablePubmedSearch: false }));

            assert.strictEqual(installClineMcpServers(mockContext, '/usr/bin/python3'), true);
            const written = JSON.parse(fs.readFileSync(clineSettingsPath, 'utf-8'));
            assert.ok(written.mcpServers['zotero-keeper']);
            assert.strictEqual(written.mcpServers['pubmed-search-mcp'], undefined);
        });

        it('refuses to overwrite the only copy of an unparsable file when the backup fails', () => {
            seed('{ not json');
            sinon.stub(fileSystem, 'copyFileSync').throws(new Error('backup disk full'));

            assert.throws(() => installClineMcpServers(mockContext, '/usr/bin/python3'), /backup disk full/);
            sinon.restore();
            assert.strictEqual(fs.readFileSync(clineSettingsPath, 'utf-8'), '{ not json');
        });

        it('leaves no temp files and keeps the old settings when the write fails', () => {
            seed(JSON.stringify({ mcpServers: { mine: { command: 'node', args: [] } } }));
            const before = fs.readFileSync(clineSettingsPath, 'utf-8');
            sinon.stub(fileSystem, 'renameSync').throws(new Error('EBUSY'));

            assert.strictEqual(installClineMcpServers(mockContext, '/usr/bin/python3'), false);
            sinon.restore();
            assert.strictEqual(fs.readFileSync(clineSettingsPath, 'utf-8'), before);
            assert.deepStrictEqual(fs.readdirSync(path.dirname(clineSettingsPath)), ['cline_mcp_settings.json']);
        });
    });
});
