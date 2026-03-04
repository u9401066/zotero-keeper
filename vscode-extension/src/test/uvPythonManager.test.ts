import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import * as assert from 'assert';
import { UvPythonManager } from '../uvPythonManager.js';
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

    describe('showOutput', () => {
        it('should not throw', () => {
            manager = new UvPythonManager(ctx as any);
            assert.doesNotThrow(() => manager.showOutput());
        });
    });
});
