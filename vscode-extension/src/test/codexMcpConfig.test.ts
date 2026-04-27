/**
 * Unit tests for Codex MCP configuration manager
 */

import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import {
    installCodexMcpServers,
    removeCodexMcpServers,
    getCodexHome,
    getCodexConfigPath,
    isCodexAvailable,
    __test__,
} from '../codexMcpConfig.js';

describe('codexMcpConfig', () => {
    let tmpDir: string;
    let configPath: string;
    let originalCodexHome: string | undefined;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'zotero-mcp-codex-test-'));
        originalCodexHome = process.env.CODEX_HOME;
        process.env.CODEX_HOME = tmpDir;
        configPath = path.join(tmpDir, 'config.toml');
    });

    afterEach(() => {
        if (originalCodexHome === undefined) {
            delete process.env.CODEX_HOME;
        } else {
            process.env.CODEX_HOME = originalCodexHome;
        }
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    describe('path resolution', () => {
        it('honors CODEX_HOME', () => {
            assert.strictEqual(getCodexHome(), tmpDir);
            assert.strictEqual(getCodexConfigPath(), configPath);
        });

        it('falls back to ~/.codex when CODEX_HOME unset', () => {
            delete process.env.CODEX_HOME;
            assert.strictEqual(getCodexHome(), path.join(os.homedir(), '.codex'));
        });
    });

    describe('isCodexAvailable', () => {
        it('returns true when CODEX_HOME directory exists', () => {
            // tmpDir already exists from mkdtempSync
            assert.strictEqual(isCodexAvailable(), true);
        });

        it('returns false when CODEX_HOME directory does not exist', () => {
            fs.rmSync(tmpDir, { recursive: true, force: true });
            assert.strictEqual(isCodexAvailable(), false);
        });
    });

    describe('escapeTomlString', () => {
        it('escapes Windows backslashes', () => {
            assert.strictEqual(
                __test__.escapeTomlString('C:\\Users\\foo'),
                'C:\\\\Users\\\\foo'
            );
        });

        it('escapes embedded double quotes', () => {
            assert.strictEqual(__test__.escapeTomlString('a"b'), 'a\\"b');
        });
    });

    describe('renderManagedBlock', () => {
        it('renders command, args, and sorted env subtable', () => {
            const block = __test__.renderManagedBlock('zotero-keeper', {
                command: '/usr/bin/python3',
                args: ['-m', 'zotero_mcp'],
                env: { ZOTERO_PORT: '23119', ZOTERO_HOST: 'localhost' },
            });
            assert.ok(block.includes('[mcp_servers.zotero-keeper]'));
            assert.ok(block.includes('command = "/usr/bin/python3"'));
            assert.ok(block.includes('args = ["-m", "zotero_mcp"]'));
            assert.ok(block.includes('[mcp_servers.zotero-keeper.env]'));
            // Env keys should be sorted alphabetically
            const hostIdx = block.indexOf('ZOTERO_HOST');
            const portIdx = block.indexOf('ZOTERO_PORT');
            assert.ok(hostIdx > 0 && portIdx > hostIdx);
        });

        it('omits env subtable when env is empty', () => {
            const block = __test__.renderManagedBlock('foo', {
                command: 'x',
                args: [],
                env: {},
            });
            assert.ok(!block.includes('.env]'));
        });
    });

    describe('stripManagedBlock', () => {
        it('removes the table and its env subtable', () => {
            const input = [
                '[mcp_servers.other]',
                'command = "other"',
                '',
                '[mcp_servers.zotero-keeper]',
                'command = "old-py"',
                'args = ["-m", "zotero_mcp"]',
                '',
                '[mcp_servers.zotero-keeper.env]',
                'ZOTERO_HOST = "localhost"',
                '',
                '[other_section]',
                'key = "value"',
                '',
            ].join('\n');
            const result = __test__.stripManagedBlock(input, 'zotero-keeper');
            assert.strictEqual(result.removed, true);
            assert.ok(!result.content.includes('zotero-keeper'));
            assert.ok(result.content.includes('[mcp_servers.other]'));
            assert.ok(result.content.includes('[other_section]'));
        });

        it('is a no-op when block does not exist', () => {
            const input = '[other]\nkey = "value"\n';
            const result = __test__.stripManagedBlock(input, 'zotero-keeper');
            assert.strictEqual(result.removed, false);
            assert.strictEqual(result.content, input);
        });
    });

    describe('installCodexMcpServers', () => {
        it('creates config.toml with both managed servers when none exist', () => {
            const updated = installCodexMcpServers('/usr/bin/python3');
            assert.strictEqual(updated, true);
            assert.ok(fs.existsSync(configPath));

            const content = fs.readFileSync(configPath, 'utf-8');
            assert.ok(content.includes('[mcp_servers.zotero-keeper]'));
            assert.ok(content.includes('[mcp_servers.pubmed-search-mcp]'));
            assert.ok(content.includes('command = "/usr/bin/python3"'));
            assert.ok(content.includes('args = ["-m", "zotero_mcp"]'));
            assert.ok(content.includes('args = ["-m", "pubmed_search.presentation.mcp_server"]'));
        });

        it('preserves unrelated user content (other tables and comments)', () => {
            const userContent = [
                '# user comment at top',
                '',
                '[other_server]',
                'command = "node"',
                'args = ["server.js"]',
                '',
                '[mcp_servers.user-tool]',
                'command = "user-tool"',
                '',
            ].join('\n');
            fs.writeFileSync(configPath, userContent, 'utf-8');

            const updated = installCodexMcpServers('/usr/bin/python3');
            assert.strictEqual(updated, true);

            const content = fs.readFileSync(configPath, 'utf-8');
            assert.ok(content.includes('# user comment at top'));
            assert.ok(content.includes('[other_server]'));
            assert.ok(content.includes('[mcp_servers.user-tool]'));
            assert.ok(content.includes('[mcp_servers.zotero-keeper]'));
            assert.ok(content.includes('[mcp_servers.pubmed-search-mcp]'));
        });

        it('updates existing managed blocks when python path changes', () => {
            installCodexMcpServers('/old/python');
            const before = fs.readFileSync(configPath, 'utf-8');
            assert.ok(before.includes('command = "/old/python"'));

            const updated = installCodexMcpServers('/new/python');
            assert.strictEqual(updated, true);

            const after = fs.readFileSync(configPath, 'utf-8');
            assert.ok(!after.includes('/old/python'));
            assert.ok(after.includes('command = "/new/python"'));
            // No duplicated blocks
            assert.strictEqual((after.match(/\[mcp_servers\.zotero-keeper\]/g) || []).length, 1);
            assert.strictEqual((after.match(/\[mcp_servers\.pubmed-search-mcp\]/g) || []).length, 1);
        });

        it('is idempotent when nothing changes', () => {
            installCodexMcpServers('/usr/bin/python3');
            const updated = installCodexMcpServers('/usr/bin/python3');
            assert.strictEqual(updated, false);
        });

        it('returns false when CODEX_HOME does not exist and no force flag', () => {
            fs.rmSync(tmpDir, { recursive: true, force: true });
            const updated = installCodexMcpServers('/usr/bin/python3');
            assert.strictEqual(updated, false);
        });
    });

    describe('removeCodexMcpServers', () => {
        it('removes both managed blocks while preserving other content', () => {
            installCodexMcpServers('/usr/bin/python3');
            const userExtra = '\n[other]\nkey = "value"\n';
            fs.appendFileSync(configPath, userExtra);

            const removed = removeCodexMcpServers();
            assert.strictEqual(removed, true);

            const content = fs.readFileSync(configPath, 'utf-8');
            assert.ok(!content.includes('[mcp_servers.zotero-keeper]'));
            assert.ok(!content.includes('[mcp_servers.pubmed-search-mcp]'));
            assert.ok(content.includes('[other]'));
        });

        it('returns false when no managed blocks exist', () => {
            fs.writeFileSync(configPath, '[other]\nkey = "value"\n', 'utf-8');
            const removed = removeCodexMcpServers();
            assert.strictEqual(removed, false);
        });

        it('returns false when config file does not exist', () => {
            const removed = removeCodexMcpServers();
            assert.strictEqual(removed, false);
        });
    });
});
