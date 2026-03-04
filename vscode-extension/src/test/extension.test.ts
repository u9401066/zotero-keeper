import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import * as assert from 'assert';

/**
 * Extension module tests.
 *
 * The extension.ts module has side effects on import (module-level variables)
 * and heavily depends on VS Code APIs. We test the exported functions via
 * dynamic import after mocks are set up.
 */
describe('Extension Module', () => {
    beforeEach(() => {
        sinon.restore();
    });

    afterEach(() => {
        sinon.restore();
    });

    describe('activate', () => {
        it('should export activate function', async () => {
            // Dynamic import to ensure mock-vscode is loaded first
            const ext = await import('../extension.js');
            assert.strictEqual(typeof ext.activate, 'function');
        });

        it('should export deactivate function', async () => {
            const ext = await import('../extension.js');
            assert.strictEqual(typeof ext.deactivate, 'function');
        });
    });

    describe('deactivate', () => {
        it('should not throw when called', async () => {
            const ext = await import('../extension.js');
            assert.doesNotThrow(() => ext.deactivate());
        });
    });
});
