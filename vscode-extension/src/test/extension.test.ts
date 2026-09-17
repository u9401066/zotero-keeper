import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import type * as vscode from 'vscode';
import * as assert from 'assert';
import { workspace } from './mock-vscode';
import * as harness from '../harnessAssets';

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
        workspace.workspaceFolders = undefined;
        workspace.isTrusted = true;
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

    describe('harness activation policy', () => {
        const context = { extensionPath: '/extension', extension: { packageJSON: { version: '0.9.0' } } } as unknown as vscode.ExtensionContext;
        it('does not install on ordinary activation when the setting is off', async () => {
            const install = sinon.stub(harness, 'installHarnessAssets');
            workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
            workspace.getConfiguration.returns({ get: (_key: string, fallback: unknown) => fallback });
            const ext = await import('../extension.js');
            await ext.installCopilotInstructions(context, 'auto');
            assert.ok(install.notCalled);
        });
        it('does not install hooks into an untrusted workspace even manually', async () => {
            const install = sinon.stub(harness, 'installHarnessAssets');
            workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
            workspace.isTrusted = false;
            const ext = await import('../extension.js');
            await ext.installCopilotInstructions(context, 'manual');
            assert.ok(install.notCalled);
        });
        it('uses the preservation installer for an explicit manual request', async () => {
            const install = sinon.stub(harness, 'installHarnessAssets').returns({ installed: [], updated: [], preserved: ['AGENTS.md'], unchanged: [] });
            workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
            const ext = await import('../extension.js');
            await ext.installCopilotInstructions(context, 'manual');
            assert.ok(install.calledOnce);
            assert.strictEqual(install.firstCall.args[2], '0.9.0');
        });
    });
});
