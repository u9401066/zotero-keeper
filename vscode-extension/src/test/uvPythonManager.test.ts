import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import {
    buildAtomicPackageInstallCommand,
    UvPythonManager,
} from '../uvPythonManager.js';
import { PUBMED_SEARCH_PACKAGE } from '../pubmedSearchPackage.js';
import { ZOTERO_KEEPER_PACKAGE } from '../zoteroKeeperPackage.js';
import { createMockContext } from './mock-vscode.js';

describe('UvPythonManager', () => {
    let manager: UvPythonManager;
    let ctx: ReturnType<typeof createMockContext>;

    beforeEach(() => {
        sinon.restore();
        ctx = createMockContext();
    });

    afterEach(() => {
        sinon.restore();
    });

    describe('constructor', () => {
        it('should initialize (not ready when no files exist)', () => {
            manager = new UvPythonManager(ctx as any);
            // In fresh test context with mock storage path, files don't exist
            assert.strictEqual(manager.isReady(), false);
        });
    });

    describe('isReady', () => {
        it('should return false initially', () => {
            manager = new UvPythonManager(ctx as any);
            assert.strictEqual(manager.isReady(), false);
        });
    });

    describe('getPythonPath', () => {
        it('should return venv python path on Linux', () => {
            if (process.platform === 'win32') { return; }

            manager = new UvPythonManager(ctx as any);
            const pythonPath = manager.getPythonPath();
            assert.ok(pythonPath.endsWith('bin/python'));
            assert.ok(pythonPath.includes('venv'));
        });
    });

    describe('getPythonVersion', () => {
        it('should return undefined when not ready', async () => {
            manager = new UvPythonManager(ctx as any);
            const version = await manager.getPythonVersion();
            assert.strictEqual(version, undefined);
        });
    });

    describe('verifyReady', () => {
        it('should return false when python binary does not exist', async () => {
            manager = new UvPythonManager(ctx as any);
            const ready = await manager.verifyReady();
            assert.strictEqual(ready, false);
        });
    });

    describe('package installation', () => {
        it('builds one force-reinstall resolver command containing both MCP packages', () => {
            const uvPath = process.platform === 'win32'
                ? 'C:\\extension storage\\uv.exe'
                : '/extension storage/uv';
            const pythonPath = process.platform === 'win32'
                ? 'C:\\extension storage\\venv\\Scripts\\python.exe'
                : '/extension storage/venv/bin/python';

            const command = buildAtomicPackageInstallCommand(
                uvPath,
                pythonPath,
                [ZOTERO_KEEPER_PACKAGE, PUBMED_SEARCH_PACKAGE],
            );

            assert.strictEqual((command.match(/\bpip install\b/g) ?? []).length, 1);
            assert.ok(command.includes('--upgrade --force-reinstall'));
            assert.ok(command.includes(`"${ZOTERO_KEEPER_PACKAGE}"`));
            assert.ok(command.includes(`"${PUBMED_SEARCH_PACKAGE}"`));
            assert.ok(command.includes(`--python "${pythonPath}"`));
        });

        it('invokes the atomic package command once instead of looping per package', () => {
            const sourcePath = path.resolve(__dirname, '..', 'uvPythonManager.js')
                .replace(`${path.sep}out${path.sep}`, `${path.sep}src${path.sep}`)
                .replace(/\.js$/, '.ts');
            const source = fs.readFileSync(sourcePath, 'utf-8');
            const methodStart = source.indexOf('private async installPackages(');
            const methodEnd = source.indexOf('\n    /**\n     * Upgrade packages', methodStart);
            const method = source.slice(methodStart, methodEnd);

            assert.ok(method.includes('buildAtomicPackageInstallCommand('));
            assert.strictEqual((method.match(/execSync\(cmd/g) ?? []).length, 1);
            assert.ok(!method.includes('for (const pkg of REQUIRED_PACKAGES)'));
        });
    });

    describe('showOutput', () => {
        it('should not throw', () => {
            manager = new UvPythonManager(ctx as any);
            assert.doesNotThrow(() => manager.showOutput());
        });
    });
});
