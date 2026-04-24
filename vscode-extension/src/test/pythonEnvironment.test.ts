import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as assert from 'assert';
import { PythonEnvironment } from '../pythonEnvironment.js';
import { createMockContext } from './mock-vscode.js';
import {
    PUBMED_SEARCH_FIXED_COMMIT,
    PUBMED_SEARCH_PACKAGE,
    PUBMED_SEARCH_VERSION,
    compareDottedVersions,
} from '../pubmedSearchPackage.js';

describe('PythonEnvironment', () => {
    let env: PythonEnvironment;
    let ctx: ReturnType<typeof createMockContext>;

    beforeEach(() => {
        sinon.restore();
        ctx = createMockContext();
        env = new PythonEnvironment(ctx as any);
    });

    afterEach(() => {
        env.dispose();
        sinon.restore();
    });

    describe('constructor', () => {
        it('should start with null python path', () => {
            assert.strictEqual(env.getPythonPath(), null);
        });
    });

    describe('getPythonPath', () => {
        it('should return null before ensurePython is called', () => {
            assert.strictEqual(env.getPythonPath(), null);
        });
    });

    describe('getPythonVersion', () => {
        it('should return null when python path is not set', async () => {
            const version = await env.getPythonVersion();
            assert.strictEqual(version, null);
        });
    });

    describe('checkPackages', () => {
        it('should return false when python path is not set', async () => {
            const result = await env.checkPackages();
            assert.strictEqual(result, false);
        });
    });

    describe('installPackages', () => {
        it('should return false when python path is not set', async () => {
            const result = await env.installPackages();
            assert.strictEqual(result, false);
        });
    });

    describe('PubMed package policy', () => {
        it('should pin PubMed installs to the fixed upstream commit archive', () => {
            assert.ok(PUBMED_SEARCH_PACKAGE.includes(PUBMED_SEARCH_FIXED_COMMIT));
            assert.ok(PUBMED_SEARCH_PACKAGE.startsWith('pubmed-search-mcp @ https://github.com/'));
        });

        it('should compare version baselines numerically', () => {
            assert.strictEqual(compareDottedVersions('0.5.5', PUBMED_SEARCH_VERSION) < 0, true);
            assert.strictEqual(compareDottedVersions(PUBMED_SEARCH_VERSION, '0.5.6'), 0);
            assert.strictEqual(compareDottedVersions('0.5.7', PUBMED_SEARCH_VERSION) > 0, true);
        });
    });

    describe('dispose', () => {
        it('should not throw', () => {
            assert.doesNotThrow(() => env.dispose());
        });
    });
});
