import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as assert from 'assert';
import * as vscode from 'vscode';
import childProcess from 'child_process';
import { PythonEnvironment } from '../pythonEnvironment.js';
import { createMockContext, MockWorkspaceConfiguration } from './mock-vscode.js';
import {
    PUBMED_SEARCH_FIXED_COMMIT,
    PUBMED_SEARCH_PACKAGE,
    PUBMED_SEARCH_SOURCE_URL,
    compareDottedVersions,
} from '../pubmedSearchPackage.js';
import { ZOTERO_KEEPER_PACKAGE, ZOTERO_KEEPER_SOURCE_URL } from '../zoteroKeeperPackage.js';

describe('compareDottedVersions', () => {
    const cases: Array<[string, string, number]> = [
        ['0.7.10', '0.7.9', 1],
        ['0.7.9', '0.7.9', 0],
        ['0.7.2', '0.7.9', -1],
        ['1.0', '1.0.0', 0],
        ['1', '1.0.1', -1],
        ['3.5.0.post1', '3.5.0', 0],
        ['10.0.0', '9.9.9', 1],
        ['1.0.0rc1', '1.0.0', 0],
    ];
    for (const [actual, expected, sign] of cases) {
        it(`${actual} vs ${expected} -> ${sign}`, () => {
            assert.strictEqual(Math.sign(compareDottedVersions(actual, expected)), sign);
        });
    }

    it('never lets a malformed installed version satisfy a minimum', () => {
        for (const bad of ['', 'unknown', '..', 'v', 'abc.def']) {
            assert.ok(compareDottedVersions(bad, '0.0.1') < 0, `"${bad}" must compare below 0.0.1`);
        }
    });
});

describe('pinned package specifiers', () => {
    it('install from the pinned archives, not from an index', () => {
        assert.ok(ZOTERO_KEEPER_PACKAGE.startsWith('zotero-keeper @ '));
        assert.ok(ZOTERO_KEEPER_PACKAGE.includes(`${ZOTERO_KEEPER_SOURCE_URL}#subdirectory=mcp-server`));
        assert.ok(PUBMED_SEARCH_PACKAGE.startsWith('pubmed-search-mcp @ '));
        assert.ok(PUBMED_SEARCH_SOURCE_URL.includes(PUBMED_SEARCH_FIXED_COMMIT));
        assert.match(PUBMED_SEARCH_FIXED_COMMIT, /^[0-9a-f]{40}$/);
    });
});

describe('PythonEnvironment', () => {
    let env: PythonEnvironment;
    let execFile: sinon.SinonStub;

    /** Fake interpreters: path -> `python --version` output (absent = cannot execute). */
    function fakeSystem(options: { interpreters: Record<string, string>; lookups?: Record<string, string[]> }): void {
        execFile.callsFake((file: string, args: string[], ...rest: unknown[]) => {
            const callback = rest[rest.length - 1] as (err: Error | null, stdout: string, stderr: string) => void;
            const isLocator = file === 'where' || file === 'which';
            if (isLocator) {
                const found = options.lookups?.[args[0]] ?? [];
                setImmediate(() => found.length
                    ? callback(null, found.join('\r\n') + '\r\n', '')
                    : callback(new Error('not found'), '', ''));
            } else if (args[0] === '--version' && options.interpreters[file]) {
                setImmediate(() => callback(null, options.interpreters[file], ''));
            } else {
                setImmediate(() => callback(new Error(`spawn ${file} ENOENT`), '', ''));
            }
            return {};
        });
    }

    const configure = (values: Record<string, unknown>): void => {
        (vscode.workspace.getConfiguration as sinon.SinonStub).returns(new MockWorkspaceConfiguration(values));
    };

    beforeEach(() => {
        sinon.restore();
        execFile = sinon.stub(childProcess, 'execFile');
        (vscode.extensions.getExtension as sinon.SinonStub).returns(undefined);
        env = new PythonEnvironment(createMockContext());
    });

    afterEach(() => {
        env.dispose();
        sinon.restore();
    });

    it('does nothing without a known interpreter', async () => {
        assert.strictEqual(env.getPythonPath(), null);
        assert.strictEqual(await env.getPythonVersion(), null);
        assert.strictEqual(await env.checkPackages(), false);
        assert.strictEqual(await env.installPackages(), false);
        assert.ok(execFile.notCalled);
    });

    it('runs a configured interpreter verbatim with no shell, even if its path looks like injection', async () => {
        const hostile = 'C:\\Program Files\\Py" & calc & "\\python.exe';
        configure({ pythonPath: hostile });
        fakeSystem({ interpreters: { [hostile]: 'Python 3.12.4\n' } });

        assert.strictEqual(await env.ensurePython(), hostile);

        const call = execFile.firstCall;
        assert.strictEqual(call.args[0], hostile);
        assert.deepStrictEqual(call.args[1], ['--version']);
        assert.ok(!(call.args[2] as { shell?: unknown }).shell, 'no shell may be involved');
    });

    it('rejects interpreters older than 3.12 and takes the next candidate', async () => {
        configure({ pythonPath: '/old/python' });
        fakeSystem({
            interpreters: { '/old/python': 'Python 3.11.9\n', '/usr/bin/python3': 'Python 3.13.0\n' },
            lookups: { python3: ['/usr/bin/python3'] },
        });
        assert.strictEqual(await env.ensurePython(), '/usr/bin/python3');
    });

    it('skips an unusable first PATH hit (Windows Store alias) and uses a later real interpreter', async () => {
        configure({ pythonPath: '' });
        fakeSystem({
            interpreters: { 'C:\\Python312\\python.exe': 'Python 3.12.2\n' },
            lookups: { python3: ['C:\\Users\\u\\AppData\\Local\\Microsoft\\WindowsApps\\python3.exe', 'C:\\Python312\\python.exe'] },
        });
        assert.strictEqual(await env.ensurePython(), 'C:\\Python312\\python.exe');
        assert.strictEqual(env.getPythonPath(), 'C:\\Python312\\python.exe');
    });

    it('accepts Python 4+ and rejects non-Python output', async () => {
        configure({ pythonPath: '/a' });
        fakeSystem({ interpreters: { '/a': 'Python 4.0.1\n' } });
        assert.strictEqual(await env.ensurePython(), '/a');

        env = new PythonEnvironment(createMockContext());
        configure({ pythonPath: '/b' });
        fakeSystem({ interpreters: { '/b': 'Ruby 3.3\n' }, lookups: {} });
        assert.strictEqual(await env.ensurePython(), null);
    });
});
