import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as cp from 'child_process';
import * as fs from 'fs';
import * as assert from 'assert';
import { PythonEnvironment } from '../pythonEnvironment.js';
import { createMockContext } from './mock-vscode.js';

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

    describe('dispose', () => {
        it('should not throw', () => {
            assert.doesNotThrow(() => env.dispose());
        });
    });
});
