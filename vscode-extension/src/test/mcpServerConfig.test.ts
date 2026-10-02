import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import fileSystem from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as sinon from 'sinon';
import childProcess from 'child_process';
import {
    buildPubmedEnv,
    buildZoteroEnv,
    getGitEmail,
    redactCredentials,
    resetGitEmailCache,
    writeFileAtomic,
} from '../mcpServerConfig.js';
import { PUBMED_WORKSPACE_DIR_ENV } from '../pubmedSearchPackage.js';
import { MockWorkspaceConfiguration } from './mock-vscode.js';

describe('mcpServerConfig', () => {
    let gitStub: sinon.SinonStub;

    beforeEach(() => {
        resetGitEmailCache();
        gitStub = sinon.stub(childProcess, 'execFileSync').returns('git.user@example.org\n');
    });

    afterEach(() => {
        sinon.restore();
        resetGitEmailCache();
    });

    describe('buildZoteroEnv', () => {
        it('stringifies the port and falls back to loopback defaults', () => {
            assert.deepStrictEqual(buildZoteroEnv(new MockWorkspaceConfiguration()), {
                ZOTERO_HOST: 'localhost',
                ZOTERO_PORT: '23119',
            });
            assert.deepStrictEqual(
                buildZoteroEnv(new MockWorkspaceConfiguration({ zoteroHost: '127.0.0.1', zoteroPort: 9999 })),
                { ZOTERO_HOST: '127.0.0.1', ZOTERO_PORT: '9999' },
            );
        });
    });

    describe('buildPubmedEnv', () => {
        it('maps every setting to its environment variable', () => {
            const env = buildPubmedEnv(new MockWorkspaceConfiguration({
                ncbiEmail: 'me@example.org',
                ncbiApiKey: 'ncbi',
                coreApiKey: 'core',
                openAlexApiKey: 'oa',
                semanticScholarApiKey: 's2',
                httpProxy: 'http://p:1',
                httpsProxy: 'https://p:2',
                openUrlPreset: 'ntu',
                openUrlResolver: 'https://resolver.example/openurl',
            }), '/work/space');
            assert.deepStrictEqual(env, {
                NCBI_EMAIL: 'me@example.org',
                NCBI_API_KEY: 'ncbi',
                CORE_API_KEY: 'core',
                OPENALEX_API_KEY: 'oa',
                S2_API_KEY: 's2',
                HTTP_PROXY: 'http://p:1',
                HTTPS_PROXY: 'https://p:2',
                OPENURL_PRESET: 'ntu',
                OPENURL_RESOLVER: 'https://resolver.example/openurl',
                [PUBMED_WORKSPACE_DIR_ENV]: '/work/space',
            });
            assert.ok(gitStub.notCalled, 'an explicit email must not trigger a git lookup');
        });

        it('omits empty and whitespace-only values', () => {
            const env = buildPubmedEnv(new MockWorkspaceConfiguration({
                ncbiEmail: '  ',
                ncbiApiKey: '   ',
                coreApiKey: '',
            }));
            assert.deepStrictEqual(env, { NCBI_EMAIL: 'git.user@example.org' });
        });

        it('falls back to git user.email, in the workspace folder, when no email is set', () => {
            const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'zk-git-'));
            try {
                const env = buildPubmedEnv(new MockWorkspaceConfiguration(), workspace);
                assert.strictEqual(env.NCBI_EMAIL, 'git.user@example.org');
                const [file, args, options] = gitStub.firstCall.args;
                assert.strictEqual(file, 'git');
                assert.deepStrictEqual(args, ['config', 'user.email']);
                assert.strictEqual(options.cwd, workspace);
            } finally {
                fs.rmSync(workspace, { recursive: true, force: true });
            }
        });
    });

    describe('getGitEmail', () => {
        it('returns an empty string when git is unavailable', () => {
            gitStub.throws(new Error('spawn git ENOENT'));
            assert.strictEqual(getGitEmail(), '');
        });

        it('caches lookups, including failures, so provider refreshes do not respawn git', () => {
            gitStub.throws(new Error('not a repo'));
            getGitEmail('/a');
            getGitEmail('/a');
            assert.strictEqual(gitStub.callCount, 1);
            getGitEmail('/b');
            assert.strictEqual(gitStub.callCount, 2);
        });

        it('ignores a workspace folder that does not exist instead of failing the spawn', () => {
            getGitEmail(path.join(os.tmpdir(), 'zk-definitely-missing-dir'));
            assert.strictEqual(gitStub.firstCall.args[2].cwd, undefined);
        });
    });

    describe('writeFileAtomic', () => {
        let dir: string;
        beforeEach(() => { dir = fs.mkdtempSync(path.join(os.tmpdir(), 'zk-atomic-')); });
        afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

        it('creates missing parent directories and leaves no temp files', () => {
            const target = path.join(dir, 'a', 'b', 'config.json');
            writeFileAtomic(target, '{"ok":true}');
            assert.strictEqual(fs.readFileSync(target, 'utf-8'), '{"ok":true}');
            assert.deepStrictEqual(fs.readdirSync(path.dirname(target)), ['config.json']);
        });

        it('creates new files owner-only because they hold API keys', function () {
            if (process.platform === 'win32') { this.skip(); }
            const target = path.join(dir, 'secret.toml');
            writeFileAtomic(target, 'KEY = "v"');
            assert.strictEqual(fs.statSync(target).mode & 0o777, 0o600);
        });

        it('keeps the permission bits of a file it replaces', function () {
            if (process.platform === 'win32') { this.skip(); }
            const target = path.join(dir, 'shared.toml');
            fs.writeFileSync(target, 'old');
            fs.chmodSync(target, 0o640);
            writeFileAtomic(target, 'new');
            assert.strictEqual(fs.readFileSync(target, 'utf-8'), 'new');
            assert.strictEqual(fs.statSync(target).mode & 0o777, 0o640);
        });

        it('refuses a read-only target and leaves it and the directory untouched', function () {
            if (typeof process.getuid === 'function' && process.getuid() === 0) { this.skip(); }
            const target = path.join(dir, 'locked.json');
            fs.writeFileSync(target, 'original');
            fs.chmodSync(target, 0o444);
            try {
                assert.throws(() => writeFileAtomic(target, 'changed'));
                assert.strictEqual(fs.readFileSync(target, 'utf-8'), 'original');
                assert.deepStrictEqual(fs.readdirSync(dir), ['locked.json']);
            } finally {
                fs.chmodSync(target, 0o644);
            }
        });

        it('removes its temp file when the final rename fails', () => {
            const target = path.join(dir, 'config.json');
            sinon.stub(fileSystem, 'renameSync').throws(new Error('disk failure'));
            assert.throws(() => writeFileAtomic(target, 'x'), /disk failure/);
            sinon.restore();
            assert.deepStrictEqual(fs.readdirSync(dir), []);
        });
    });

    describe('redactCredentials', () => {
        it('strips user:password@ and leaves credential-free URLs alone', () => {
            assert.strictEqual(redactCredentials('http://u:p@proxy:8080'), 'http://***@proxy:8080');
            assert.strictEqual(redactCredentials('http://proxy:8080'), 'http://proxy:8080');
        });
    });
});
