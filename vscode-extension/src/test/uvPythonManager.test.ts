import { describe, it, beforeEach, afterEach } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { EventEmitter } from 'events';
import { Readable } from 'stream';
import * as sinon from 'sinon';
import type * as http from 'http';
import {
    UvPythonManager,
    assertSha256,
    buildProcessPathPattern,
    downloadFile,
    parsePids,
    sha256OfFile,
} from '../uvPythonManager.js';
import { buildAtomicPackageInstallArgs } from '../uvCommands.js';
import { PUBMED_SEARCH_PACKAGE } from '../pubmedSearchPackage.js';
import { ZOTERO_KEEPER_PACKAGE } from '../zoteroKeeperPackage.js';
import { createMockContext } from './mock-vscode.js';

describe('uv install commands', () => {
    it('builds ONE resolver invocation; each package stays a single argument (no shell quoting)', () => {
        const python = path.join('C:', 'extension storage', 'venv', 'python.exe');
        const args = buildAtomicPackageInstallArgs(python, [ZOTERO_KEEPER_PACKAGE, PUBMED_SEARCH_PACKAGE]);

        assert.deepStrictEqual(args.slice(0, 4), ['pip', 'install', '--upgrade', '--force-reinstall']);
        assert.strictEqual(args.filter(a => a === 'install').length, 1);
        assert.strictEqual(args[args.indexOf('--python') + 1], python);
        // "name @ url#subdirectory=..." contains spaces and must survive as one argv entry.
        assert.deepStrictEqual(args.slice(-2), [ZOTERO_KEEPER_PACKAGE, PUBMED_SEARCH_PACKAGE]);
        assert.ok(args.every(a => !a.startsWith('"')));
    });
});

describe('uv download integrity', () => {
    let dir: string;
    beforeEach(() => { dir = fs.mkdtempSync(path.join(os.tmpdir(), 'zk-uv-')); });
    afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); sinon.restore(); });

    it('accepts the exact SHA-256 (case-insensitive, surrounding whitespace ignored) and rejects anything else', () => {
        const file = path.join(dir, 'uv.tar.gz');
        fs.writeFileSync(file, 'archive bytes');
        const digest = sha256OfFile(file);

        assert.doesNotThrow(() => assertSha256(file, digest));
        assert.doesNotThrow(() => assertSha256(file, `  ${digest.toUpperCase()}\n`));
        assert.throws(() => assertSha256(file, '0'.repeat(64)), /Checksum mismatch/);
        fs.writeFileSync(file, 'tampered bytes');
        assert.throws(() => assertSha256(file, digest), /Checksum mismatch/);
    });
});

describe('downloadFile', () => {
    let dir: string;
    let dest: string;
    beforeEach(() => {
        dir = fs.mkdtempSync(path.join(os.tmpdir(), 'zk-dl-'));
        dest = path.join(dir, 'download.bin');
    });
    afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

    type Reply = { status: number; headers?: Record<string, string>; body?: string; truncate?: boolean };

    /** Fake https.get answering from a url -> reply table; records every requested url. */
    function fakeGet(table: Record<string, Reply>): { get: Parameters<typeof downloadFile>[3]; requested: string[] } {
        const requested: string[] = [];
        const get = ((url: string, callback: (response: http.IncomingMessage) => void) => {
            requested.push(url);
            const reply = table[url];
            const request = Object.assign(new EventEmitter(), {
                setTimeout: () => request,
                destroy: () => request,
            });
            setImmediate(() => {
                if (!reply) {
                    request.emit('error', new Error(`no fake for ${url}`));
                    return;
                }
                const stream = reply.truncate
                    ? new Readable({ read() { /* never ends: the peer dropped */ } })
                    : Readable.from(reply.body ? [Buffer.from(reply.body)] : []);
                if (reply.truncate) {
                    stream.push(Buffer.from(reply.body ?? ''));
                    setImmediate(() => stream.destroy());
                }
                const response = Object.assign(stream, {
                    statusCode: reply.status,
                    headers: reply.headers ?? {},
                    complete: !reply.truncate,
                });
                callback(response as unknown as http.IncomingMessage);
            });
            return request;
        }) as unknown as Parameters<typeof downloadFile>[3];
        return { get, requested };
    }

    it('writes the body, following a relative redirect', async () => {
        const { get, requested } = fakeGet({
            'https://example.org/a/uv.zip': { status: 302, headers: { location: '/mirror/uv.zip' } },
            'https://example.org/mirror/uv.zip': { status: 200, body: 'payload' },
        });
        await downloadFile('https://example.org/a/uv.zip', dest, undefined, get);
        assert.strictEqual(fs.readFileSync(dest, 'utf-8'), 'payload');
        assert.deepStrictEqual(requested, ['https://example.org/a/uv.zip', 'https://example.org/mirror/uv.zip']);
    });

    it('refuses a redirect to plain HTTP and leaves no file behind', async () => {
        const { get } = fakeGet({
            'https://example.org/uv.zip': { status: 301, headers: { location: 'http://evil.example/uv.zip' } },
        });
        await assert.rejects(downloadFile('https://example.org/uv.zip', dest, undefined, get), /non-HTTPS/);
        assert.ok(!fs.existsSync(dest));
    });

    it('refuses a non-HTTPS start URL without any request', async () => {
        const { get, requested } = fakeGet({});
        await assert.rejects(downloadFile('http://example.org/uv.zip', dest, undefined, get), /non-HTTPS/);
        assert.deepStrictEqual(requested, []);
    });

    it('rejects HTTP errors and removes the partial file', async () => {
        const { get } = fakeGet({ 'https://example.org/uv.zip': { status: 404 } });
        await assert.rejects(downloadFile('https://example.org/uv.zip', dest, undefined, get), /HTTP 404/);
        assert.ok(!fs.existsSync(dest));
    });

    it('rejects a connection that drops mid-body instead of hanging', async () => {
        const { get } = fakeGet({ 'https://example.org/uv.zip': { status: 200, body: 'half', truncate: true } });
        await assert.rejects(downloadFile('https://example.org/uv.zip', dest, undefined, get), /interrupted/);
        assert.ok(!fs.existsSync(dest));
    });

    it('gives up on redirect loops', async () => {
        const { get } = fakeGet({
            'https://example.org/loop': { status: 302, headers: { location: '/loop' } },
        });
        await assert.rejects(downloadFile('https://example.org/loop', dest, undefined, get), /Too many redirects/);
    });
});

describe('process helpers', () => {
    it('anchors the pgrep pattern to executables inside the venv and escapes regex syntax', () => {
        const venv = '/home/u.ser/storage (x)/venv';
        const pattern = new RegExp(buildProcessPathPattern(venv));

        assert.ok(pattern.test(`${venv}/bin/python -m zotero_mcp`));
        assert.ok(!pattern.test('/home/uXser/storage (x)/venv/bin/python'), 'dots must be literal');
        assert.ok(!pattern.test(`vim ${venv}/notes.txt`), 'a mere mention of the path must not match');
        assert.ok(!pattern.test(`${venv}-other/bin/python`), 'sibling directories must not match');
    });

    it('keeps only positive integer PIDs from tool output', () => {
        assert.deepStrictEqual(parsePids('123\r\n  456 \n\nabc\n-7\n0\n12x\n'), [123, 456]);
        assert.deepStrictEqual(parsePids(''), []);
    });
});

describe('UvPythonManager', () => {
    afterEach(() => sinon.restore());

    it('is not ready, and cannot verify, when the managed Python does not exist', async () => {
        const manager = new UvPythonManager(createMockContext());
        assert.strictEqual(manager.isReady(), false);
        assert.strictEqual(await manager.getPythonVersion(), undefined);
        assert.strictEqual(await manager.verifyReady(), false);
    });

    it('shares one setup between concurrent ensureReady callers', async () => {
        const manager = new UvPythonManager(createMockContext());
        const verify = sinon.stub(manager, 'verifyReady').callsFake(
            () => new Promise<boolean>(resolve => setTimeout(() => resolve(true), 20))
        );

        const [first, second] = await Promise.all([manager.ensureReady(), manager.ensureReady()]);

        assert.strictEqual(first, second);
        assert.strictEqual(verify.callCount, 1);

        // The shared run is released afterwards, so a later call starts afresh.
        await manager.ensureReady();
        assert.strictEqual(verify.callCount, 2);
    });
});
