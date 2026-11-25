/**
 * Unit tests for the Claude Code MCP configuration manager (~/.claude.json).
 */

import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as sinon from 'sinon';
import type { SinonStub } from 'sinon';
import * as vscode from 'vscode';
import {
    syncClaudeCodeMcpServers,
    removeClaudeCodeMcpServers,
    getClaudeConfigPath,
    getClaudeProjectKey,
    getClaudeCodeScope,
    isClaudeCodeAvailable,
    __test__,
} from '../claudeCodeMcpConfig.js';
import { PUBMED_SEARCH_ENTRYPOINT } from '../pubmedSearchPackage.js';
import { MockWorkspaceConfiguration, workspace } from './mock-vscode.js';

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const WINDOWS_PYTHON = 'C:\\Users\\me\\AppData\\Roaming\\Code - Insiders\\User\\globalStorage\\u9401066.vscode-zotero-mcp\\venv\\Scripts\\python.exe';
const MANUAL_PUBMED = {
    type: 'stdio',
    command: 'C:\\manual\\python.exe',
    args: ['-m', 'pubmed_search.presentation.mcp_server'],
    env: { NCBI_EMAIL: 'manual@example.org', PUBMED_WORKSPACE_DIR: 'g:\\elsewhere' },
};

describe('claudeCodeMcpConfig', () => {
    let tmpDir: string;
    let home: string;
    let configPath: string;
    let context: Pick<vscode.ExtensionContext, 'globalStorageUri'>;
    let ws: string;
    let projectKey: string;
    let originalConfigDir: string | undefined;
    const originalDelays = [...__test__.seams.lockRetryDelaysMs];

    const setSettings = (values: Record<string, unknown> = {}): void => {
        (vscode.workspace.getConfiguration as SinonStub).returns(
            new MockWorkspaceConfiguration({ ncbiEmail: 'me@example.org', ...values })
        );
    };
    const setFolders = (...folders: string[]): void => {
        workspace.workspaceFolders = folders.map(fsPath => ({ uri: { fsPath } }));
    };
    const makeRepo = (dir: string): string => {
        fs.mkdirSync(path.join(dir, '.git'), { recursive: true });
        return dir;
    };
    const raw = (): string => fs.readFileSync(configPath, 'utf-8');
    const read = (): Json => JSON.parse(raw().replace(/^\uFEFF/, ''));
    const seed = (document: unknown, indent: number | string = 2): string => {
        const text = JSON.stringify(document, null, indent);
        fs.writeFileSync(configPath, text, 'utf-8');
        return text;
    };
    const homeFiles = (): string[] => fs.readdirSync(home).sort();
    const ledgerPath = (): string => __test__.getLedgerPath(context);
    const projectServers = (key = projectKey): Json => read().projects[key].mcpServers;

    /** A trimmed-down but realistic Claude Code state file. */
    function claudeState(): Json {
        return {
            numStartups: 42,
            installMethod: 'native',
            oauthAccount: { accountUuid: 'acc-1', emailAddress: 'user@example.org' },
            cachedFeatureFlags: { large: 'x'.repeat(256), nested: { list: [1, 2.5, -3, true, null] } },
            mcpServers: {
                'pubmed-search-mcp': MANUAL_PUBMED,
                pencil: { type: 'stdio', command: 'pencil', args: ['--app', 'code'], env: {} },
            },
            projects: {
                [projectKey]: {
                    allowedTools: ['Bash(ls)'],
                    mcpContextUris: [],
                    mcpServers: { mine: { type: 'stdio', command: 'node', args: ['mine.js'] } },
                    enabledMcpjsonServers: [],
                    disabledMcpjsonServers: [],
                    hasTrustDialogAccepted: true,
                },
                '/some/other/project': { allowedTools: [], mcpServers: {} },
            },
            unicode: '研究 ✓ \u2028',
        };
    }

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'zotero-mcp-claude-test-'));
        home = path.join(tmpDir, 'home');
        fs.mkdirSync(home);
        originalConfigDir = process.env.CLAUDE_CONFIG_DIR;
        process.env.CLAUDE_CONFIG_DIR = home;
        configPath = path.join(home, '.claude.json');
        context = { globalStorageUri: { fsPath: path.join(tmpDir, 'globalStorage', 'u9401066.vscode-zotero-mcp') } as vscode.Uri };
        ws = makeRepo(path.join(tmpDir, 'ws-研究 PACU'));
        projectKey = getClaudeProjectKey(ws);
        setFolders(ws);
        setSettings();
        __test__.seams.lockRetryDelaysMs = [1, 1];
        __test__.seams.beforeCommitCheck = undefined;
    });

    afterEach(() => {
        sinon.restore();
        __test__.seams.lockRetryDelaysMs = [...originalDelays];
        __test__.seams.beforeCommitCheck = undefined;
        workspace.workspaceFolders = undefined;
        if (originalConfigDir === undefined) {
            delete process.env.CLAUDE_CONFIG_DIR;
        } else {
            process.env.CLAUDE_CONFIG_DIR = originalConfigDir;
        }
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    describe('locations', () => {
        it('honors CLAUDE_CONFIG_DIR and falls back to ~/.claude.json', () => {
            assert.strictEqual(getClaudeConfigPath(), configPath);
            delete process.env.CLAUDE_CONFIG_DIR;
            assert.strictEqual(getClaudeConfigPath(), path.join(os.homedir(), '.claude.json'));
        });

        it('only detects Claude Code once its state file exists', () => {
            assert.strictEqual(isClaudeCodeAvailable(), false);
            seed({});
            assert.strictEqual(isClaudeCodeAvailable(), true);
        });

        it('keys a Windows project like Claude Code: forward slashes, drive letter and Unicode kept', () => {
            assert.strictEqual(
                getClaudeProjectKey('z:\\研究資料\\202610PACU清醒監測', 'win32'),
                'z:/研究資料/202610PACU清醒監測',
            );
            assert.strictEqual(getClaudeProjectKey('z:\\研究資料\\sub\\', 'win32'), 'z:/研究資料/sub');
        });

        it('keys a folder inside a repository by the repository root', () => {
            const repo = makeRepo(path.join(tmpDir, 'repo'));
            const nested = path.join(repo, 'packages', 'app');
            fs.mkdirSync(nested, { recursive: true });
            assert.strictEqual(getClaudeProjectKey(nested), getClaudeProjectKey(repo));
            if (process.platform === 'win32') {
                assert.ok(!getClaudeProjectKey(nested).includes('\\'));
            }
        });

        it('matches every existing spelling of a Windows project, but compares POSIX paths exactly', () => {
            const projects = { 'G:/Work/Repo': {}, 'g:\\work\\repo\\': {}, 'g:/work/repo2': {} };
            assert.deepStrictEqual(
                __test__.matchingProjectKeys(projects, 'g:/work/repo', 'win32'),
                ['G:/Work/Repo', 'g:\\work\\repo\\'],
            );
            assert.deepStrictEqual(__test__.matchingProjectKeys(projects, 'g:/new', 'win32'), ['g:/new']);
            assert.deepStrictEqual(
                __test__.matchingProjectKeys({ '/Work/Repo': {} }, '/work/repo', 'linux'),
                ['/work/repo'],
            );
        });

        it('reads the scope setting and rejects unknown values', () => {
            assert.strictEqual(getClaudeCodeScope(new MockWorkspaceConfiguration({})), 'local');
            assert.strictEqual(getClaudeCodeScope(new MockWorkspaceConfiguration({ claudeCodeMcpScope: 'user' })), 'user');
            assert.strictEqual(getClaudeCodeScope(new MockWorkspaceConfiguration({ claudeCodeMcpScope: 'project' })), undefined);
        });
    });

    describe('formatting', () => {
        for (const [label, text] of [
            ['Claude Code output (2 spaces, LF, no final newline)', '{\n  "a": 1,\n  "b": {\n    "c": [\n      1,\n      "x"\n    ]\n  }\n}'],
            ['a CRLF file with a final newline', '{\r\n  "a": 1,\r\n  "b": []\r\n}\r\n'],
            ['a BOM and tab indentation', '\uFEFF{\n\t"a": {\n\t\t"b": null\n\t}\n}\n'],
            ['a compact single-line file', '{"a":1,"b":{"c":"d"}}'],
        ] as const) {
            it(`round-trips ${label} byte for byte`, () => {
                const format = __test__.detectFormat(text);
                assert.strictEqual(__test__.serialize(JSON.parse(text.replace(/^\uFEFF/, '')), format), text);
            });
        }

        it('hashes entries independently of key order', () => {
            assert.strictEqual(
                __test__.canonicalJson({ b: 1, a: { d: [1, { y: 2, x: 1 }], c: 'z' } }),
                __test__.canonicalJson({ a: { c: 'z', d: [1, { x: 1, y: 2 }] }, b: 1 }),
            );
        });
    });

    describe('detection and refusal', () => {
        it('does nothing until Claude Code has created its state file', async () => {
            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'not-detected');
            assert.deepStrictEqual(homeFiles(), []);
            assert.strictEqual(fs.existsSync(ledgerPath()), false);
        });

        for (const [label, content] of [
            ['invalid JSON', '{ "mcpServers": { '],
            ['JSON with comments', '{ // my config\n "mcpServers": {} }'],
            ['an empty file', ''],
            ['a JSON array', '[]'],
            ['JSON null', 'null'],
            ['a bare string', '"hello"'],
        ] as const) {
            it(`never rewrites ${label}`, async () => {
                fs.writeFileSync(configPath, content, 'utf-8');
                const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
                assert.strictEqual(result.status, 'invalid');
                assert.strictEqual(raw(), content);
                assert.deepStrictEqual(homeFiles(), ['.claude.json'], 'no backup, temp file or lock left behind');
            });
        }

        it('never rewrites a file that is not valid UTF-8', async () => {
            const bytes = Buffer.concat([Buffer.from('{"name":"'), Buffer.from([0xff, 0xfe]), Buffer.from('"}')]);
            fs.writeFileSync(configPath, bytes);
            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'invalid');
            assert.ok(fs.readFileSync(configPath).equals(bytes));
        });

        it('refuses to reinterpret containers of the wrong type', async () => {
            const cases: Array<[Json, Record<string, unknown>]> = [
                [{ projects: 'broken' }, {}],
                [{ projects: { [projectKey]: null } }, {}],
                [{ projects: { [projectKey]: { mcpServers: [] } } }, {}],
                [{ mcpServers: ['broken'] }, { claudeCodeMcpScope: 'user' }],
            ];
            for (const [document, settings] of cases) {
                setSettings(settings);
                const before = seed(document);
                const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
                assert.strictEqual(result.status, 'invalid', JSON.stringify(document));
                assert.strictEqual(raw(), before);
            }
            assert.deepStrictEqual(homeFiles(), ['.claude.json']);
        });

        it('leaves everything alone for an unknown scope value', async () => {
            setSettings({ claudeCodeMcpScope: 'project' });
            const before = seed(claudeState());
            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'failed');
            assert.strictEqual(raw(), before);
        });
    });

    describe('local scope (default)', () => {
        it('registers both servers for the workspace project and preserves everything else', async () => {
            const original = claudeState();
            seed(original);

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'updated');
            assert.strictEqual(result.scope, 'local');
            assert.deepStrictEqual(result.written.length, 2);

            const written = read();
            const servers = written.projects[projectKey].mcpServers;
            assert.deepStrictEqual(servers['zotero-keeper'], {
                type: 'stdio',
                command: WINDOWS_PYTHON,
                args: ['-m', 'zotero_mcp'],
                env: { ZOTERO_HOST: 'localhost', ZOTERO_PORT: '23119' },
            });
            assert.deepStrictEqual(servers['pubmed-search-mcp'], {
                type: 'stdio',
                command: WINDOWS_PYTHON,
                args: ['-m', PUBMED_SEARCH_ENTRYPOINT],
                env: { NCBI_EMAIL: 'me@example.org', PUBMED_WORKSPACE_DIR: ws },
            });

            // Everything except the two new entries is exactly what was there.
            delete servers['zotero-keeper'];
            delete servers['pubmed-search-mcp'];
            assert.deepStrictEqual(written, original);
        });

        it('creates an unseen project with the shape Claude Code itself would give it', async () => {
            seed({ numStartups: 1, projects: {} });
            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'updated');

            const project = read().projects[projectKey];
            assert.deepStrictEqual(Object.keys(project.mcpServers).sort(), ['pubmed-search-mcp', 'zotero-keeper']);
            assert.deepStrictEqual(project.allowedTools, []);
            assert.deepStrictEqual(project.enabledMcpjsonServers, []);
            assert.deepStrictEqual(project.disabledMcpjsonServers, []);
            assert.strictEqual(project.hasTrustDialogAccepted, false);
        });

        it('is idempotent: an unchanged configuration is not rewritten', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const before = raw();
            const mtime = fs.statSync(configPath).mtimeMs;

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'unchanged');
            assert.strictEqual(raw(), before);
            assert.strictEqual(fs.statSync(configPath).mtimeMs, mtime);
        });

        it('keeps a Windows file\'s BOM, CRLF line endings and missing final newline', async () => {
            const text = '\uFEFF' + JSON.stringify(claudeState(), null, 2).replace(/\n/g, '\r\n');
            fs.writeFileSync(configPath, text, 'utf-8');

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'updated');
            const written = raw();
            assert.ok(written.startsWith('\uFEFF{\r\n  "numStartups": 42,\r\n'));
            assert.ok(!/(^|[^\r])\n/.test(written), 'bare LF found in a CRLF file');
            assert.ok(written.endsWith('}') && !written.endsWith('\n'));
            assert.ok(projectServers()['zotero-keeper']);

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'unchanged');
        });

        it('round-trips Windows paths and Unicode exactly', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const written = read();
            assert.strictEqual(projectServers()['pubmed-search-mcp'].command, WINDOWS_PYTHON);
            assert.strictEqual(projectServers()['pubmed-search-mcp'].env.PUBMED_WORKSPACE_DIR, ws);
            assert.strictEqual(written.unicode, '研究 ✓ \u2028');
            assert.ok(raw().includes(JSON.stringify(WINDOWS_PYTHON)), 'backslashes must be JSON-escaped, not altered');
        });

        it('registers two folders of one repository once, for the first folder', async () => {
            const repo = makeRepo(path.join(tmpDir, 'mono'));
            const first = path.join(repo, 'a');
            const second = path.join(repo, 'b');
            fs.mkdirSync(first);
            fs.mkdirSync(second);
            setFolders(first, second);
            seed({ projects: {} });

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.written.length, 2);
            assert.deepStrictEqual(Object.keys(read().projects), [getClaudeProjectKey(repo)]);
            assert.strictEqual(projectServers(getClaudeProjectKey(repo))['pubmed-search-mcp'].env.PUBMED_WORKSPACE_DIR, first);
        });

        it('only withdraws registrations of the open workspace when a server is disabled', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            setSettings({ enablePubmedSearch: false });

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'updated');
            assert.deepStrictEqual(result.removed, [`local[${projectKey}] pubmed-search-mcp`]);
            assert.ok(projectServers()['zotero-keeper']);
            assert.strictEqual(projectServers()['pubmed-search-mcp'], undefined);
            assert.deepStrictEqual(read().mcpServers['pubmed-search-mcp'], MANUAL_PUBMED, 'user scope untouched');
        });

        it('writes nothing without a workspace folder (and never falls back to user scope)', async () => {
            setFolders();
            const before = seed(claudeState());
            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'unchanged');
            assert.strictEqual(raw(), before);
        });
    });

    describe('ownership', () => {
        it('never touches a user-defined entry that reuses a managed name', async () => {
            const state = claudeState();
            const mine = { command: 'node', args: ['my-zotero.js'], env: { A: '1' } };
            state.projects[projectKey].mcpServers['zotero-keeper'] = mine;
            seed(state);

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.deepStrictEqual(result.preserved, [`local[${projectKey}] zotero-keeper`]);
            assert.deepStrictEqual(projectServers()['zotero-keeper'], mine);
            assert.ok(projectServers()['pubmed-search-mcp']);

            for (const settings of [{ enableZoteroKeeper: false }, { claudeCodeMcpScope: 'off' }]) {
                setSettings(settings);
                await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
                assert.deepStrictEqual(projectServers()['zotero-keeper'], mine);
            }
        });

        it('hands a managed entry over to the user once they edit it', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const document = read();
            document.projects[projectKey].mcpServers['zotero-keeper'].env.LOG_LEVEL = 'debug';
            seed(document);
            const edited = read().projects[projectKey].mcpServers['zotero-keeper'];

            const result = await syncClaudeCodeMcpServers(context, 'C:\\new\\python.exe');
            assert.deepStrictEqual(result.preserved, [`local[${projectKey}] zotero-keeper`]);
            assert.deepStrictEqual(projectServers()['zotero-keeper'], edited);
            assert.strictEqual(projectServers()['pubmed-search-mcp'].command, 'C:\\new\\python.exe');

            setSettings({ claudeCodeMcpScope: 'off' });
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.deepStrictEqual(projectServers()['zotero-keeper'], edited);
            assert.strictEqual(projectServers()['pubmed-search-mcp'], undefined);
        });

        it('still owns its entry after Claude Code rewrote it with a different key order', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const document = read();
            const entry = document.projects[projectKey].mcpServers['zotero-keeper'];
            document.projects[projectKey].mcpServers['zotero-keeper'] = {
                env: entry.env, args: entry.args, command: entry.command, type: entry.type,
            };
            seed(document);

            const result = await syncClaudeCodeMcpServers(context, 'C:\\new\\python.exe');
            assert.strictEqual(result.preserved.length, 0);
            assert.strictEqual(projectServers()['zotero-keeper'].command, 'C:\\new\\python.exe');
        });

        it('re-creates its entry when it was deleted, like the Cline and Codex writers', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const document = read();
            delete document.projects[projectKey].mcpServers['zotero-keeper'];
            seed(document);

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'updated');
            assert.ok(projectServers()['zotero-keeper']);
        });

        it('owns nothing when its ledger is damaged, so nothing existing is overwritten', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            fs.writeFileSync(ledgerPath(), '{ damaged', 'utf-8');
            const before = raw();

            const result = await syncClaudeCodeMcpServers(context, 'C:\\new\\python.exe');
            assert.strictEqual(result.status, 'unchanged');
            assert.strictEqual(result.preserved.length, 2);
            assert.strictEqual(raw(), before);
        });

        it('withdraws every registration it owns when turned off, keeping the user\'s', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            const other = makeRepo(path.join(tmpDir, 'other-workspace'));
            setFolders(other);
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.ok(projectServers(getClaudeProjectKey(other))['zotero-keeper'], 'second workspace registered');
            assert.ok(projectServers()['zotero-keeper'], 'first workspace keeps its registration');

            setSettings({ claudeCodeMcpScope: 'off' });
            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.removed.length, 4);

            const document = read();
            const expected = claudeState();
            expected.projects[getClaudeProjectKey(other)] = document.projects[getClaudeProjectKey(other)];
            assert.deepStrictEqual(document, expected);
            assert.deepStrictEqual(document.projects[getClaudeProjectKey(other)].mcpServers, {});
            assert.deepStrictEqual(JSON.parse(fs.readFileSync(ledgerPath(), 'utf-8')).entries, {});

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'unchanged');
        });

        it('moves its registration to user scope, without a workspace directory, and back', async () => {
            const state = claudeState();
            delete state.mcpServers['pubmed-search-mcp'];
            seed(state);
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);

            setSettings({ claudeCodeMcpScope: 'user' });
            const toUser = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(toUser.removed.length, 2);
            let document = read();
            assert.deepStrictEqual(document.projects[projectKey].mcpServers, state.projects[projectKey].mcpServers);
            assert.deepStrictEqual(document.mcpServers['pubmed-search-mcp'].env, { NCBI_EMAIL: 'me@example.org' });
            assert.deepStrictEqual(document.mcpServers['zotero-keeper'].args, ['-m', 'zotero_mcp']);
            assert.ok(document.mcpServers.pencil);

            setSettings({ claudeCodeMcpScope: 'local' });
            const toLocal = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(toLocal.removed.length, 2);
            document = read();
            assert.deepStrictEqual(Object.keys(document.mcpServers), ['pencil']);
            assert.ok(document.projects[projectKey].mcpServers['pubmed-search-mcp']);
        });

        it('leaves a hand-made user-scope entry alone in user scope', async () => {
            setSettings({ claudeCodeMcpScope: 'user' });
            seed(claudeState());

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.deepStrictEqual(result.written, ['user zotero-keeper']);
            assert.deepStrictEqual(result.preserved, ['user pubmed-search-mcp']);
            assert.deepStrictEqual(read().mcpServers['pubmed-search-mcp'], MANUAL_PUBMED);
        });

        it('removeClaudeCodeMcpServers withdraws only owned entries', async () => {
            seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);

            const result = await removeClaudeCodeMcpServers(context);
            assert.strictEqual(result.status, 'updated');
            assert.deepStrictEqual(read(), claudeState());
        });
    });

    describe('concurrency and write safety', () => {
        it('waits for Claude Code\'s lock and never removes a lock it does not hold', async () => {
            const before = seed(claudeState());
            fs.mkdirSync(`${configPath}.lock`);

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'busy');
            assert.strictEqual(raw(), before);
            assert.ok(fs.statSync(`${configPath}.lock`).isDirectory());
        });

        it('proceeds once the lock holder releases it', async () => {
            seed(claudeState());
            fs.mkdirSync(`${configPath}.lock`);
            __test__.seams.lockRetryDelaysMs = [20, 40, 80, 160];
            setTimeout(() => fs.rmdirSync(`${configPath}.lock`), 10);

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'updated');
            assert.ok(!fs.existsSync(`${configPath}.lock`), 'own lock released');
        });

        it('starts over when the file changes before the rename, keeping the other writer\'s change', async () => {
            seed(claudeState());
            let concurrentWrites = 0;
            __test__.seams.beforeCommitCheck = (target) => {
                if (concurrentWrites++ > 0) { return; }
                const document = JSON.parse(fs.readFileSync(target, 'utf-8'));
                document.numStartups = 43;
                fs.writeFileSync(target, JSON.stringify(document, null, 2));
            };

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'updated');
            const document = read();
            assert.strictEqual(document.numStartups, 43);
            assert.ok(document.projects[projectKey].mcpServers['zotero-keeper']);
            assert.deepStrictEqual(homeFiles(), ['.claude.json', '.claude.json.zotero-mcp.bak']);
        });

        it('gives up without overwriting a file that keeps changing', async () => {
            seed(claudeState());
            __test__.seams.beforeCommitCheck = (target) => {
                const document = JSON.parse(fs.readFileSync(target, 'utf-8'));
                document.numStartups += 1;
                fs.writeFileSync(target, JSON.stringify(document, null, 2));
            };

            const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(result.status, 'conflict');
            const document = read();
            assert.strictEqual(document.numStartups, 45, 'every concurrent write survived');
            assert.strictEqual(document.projects[projectKey].mcpServers['zotero-keeper'], undefined);
            assert.deepStrictEqual(homeFiles(), ['.claude.json', '.claude.json.zotero-mcp.bak'], 'no temp file or lock left');
        });

        it('serializes overlapping synchronizations', async () => {
            seed(claudeState());
            const results = await Promise.all([
                syncClaudeCodeMcpServers(context, WINDOWS_PYTHON),
                syncClaudeCodeMcpServers(context, WINDOWS_PYTHON),
            ]);
            assert.deepStrictEqual(results.map(r => r.status), ['updated', 'unchanged']);
        });

        it('keeps a backup of exactly the bytes it replaced', async () => {
            const before = seed(claudeState());
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(fs.readFileSync(`${configPath}${__test__.backupSuffix}`, 'utf-8'), before);
        });

        it('creates the backup and the ledger owner-only', async function () {
            if (process.platform === 'win32') { this.skip(); }
            seed(claudeState());
            fs.chmodSync(configPath, 0o644);
            await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
            assert.strictEqual(fs.statSync(`${configPath}${__test__.backupSuffix}`).mode & 0o777, 0o600);
            assert.strictEqual(fs.statSync(ledgerPath()).mode & 0o777, 0o600);
            assert.strictEqual(fs.statSync(configPath).mode & 0o777, 0o644, 'existing mode kept');
        });

        it('does not clobber a read-only config and leaves no temp files', async function () {
            if (typeof process.getuid === 'function' && process.getuid() === 0) { this.skip(); }
            const before = seed(claudeState());
            fs.chmodSync(configPath, 0o444);
            try {
                const result = await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON);
                assert.strictEqual(result.status, 'failed');
                assert.strictEqual(raw(), before);
                assert.deepStrictEqual(homeFiles(), ['.claude.json', '.claude.json.zotero-mcp.bak']);
            } finally {
                fs.chmodSync(configPath, 0o644);
            }
        });

        it('writes through a symlinked config and keeps the link', async function () {
            const realDir = path.join(tmpDir, 'dotfiles');
            fs.mkdirSync(realDir);
            const realFile = path.join(realDir, 'claude.json');
            fs.writeFileSync(realFile, JSON.stringify(claudeState(), null, 2));
            try {
                fs.symlinkSync(realFile, configPath, 'file');
            } catch {
                this.skip(); // Windows without symlink privilege
            }

            assert.strictEqual((await syncClaudeCodeMcpServers(context, WINDOWS_PYTHON)).status, 'updated');
            assert.ok(fs.lstatSync(configPath).isSymbolicLink());
            assert.ok(JSON.parse(fs.readFileSync(realFile, 'utf-8')).projects[projectKey].mcpServers['zotero-keeper']);
        });
    });
});
