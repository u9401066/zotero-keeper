/**
 * Unit tests for Cline MCP configuration manager
 */

import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as vscode from 'vscode';
import {
    installClineMcpServers,
    removeClineMcpServers,
    isClineInstalled,
} from '../clineMcpConfig.js';

// Minimal mock of ExtensionContext
function createMockContext(globalStoragePath: string): any {
    return {
        globalStorageUri: { fsPath: globalStoragePath },
    };
}

describe('clineMcpConfig', () => {
    let tmpDir: string;
    let mockContext: any;
    let clineSettingsPath: string;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'zotero-mcp-test-'));
        mockContext = createMockContext(path.join(tmpDir, 'globalStorage', 'u9401066.vscode-zotero-mcp'));
        clineSettingsPath = path.join(tmpDir, 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json');
        (vscode.extensions.getExtension as any).resetBehavior();
        (vscode.extensions.getExtension as any).returns(undefined);
    });

    afterEach(() => {
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
            (vscode.extensions.getExtension as any).withArgs('saoudrizwan.claude-dev').returns({ id: 'saoudrizwan.claude-dev' });
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
            (vscode.extensions.getExtension as any).withArgs('saoudrizwan.claude-dev').returns({ id: 'saoudrizwan.claude-dev' });

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
});
