import { describe, it, beforeEach, afterEach } from 'mocha';
import * as sinon from 'sinon';
import type * as vscode from 'vscode';
import * as vscodeApi from 'vscode';
import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { MockWorkspaceConfiguration, Uri, createMockContext, workspace } from './mock-vscode';
import * as harness from '../harnessAssets';
import { PythonEnvironment } from '../pythonEnvironment';
import { UvPythonManager } from '../uvPythonManager';

const manifest = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '..', '..', 'package.json'), 'utf-8')
) as { contributes: { commands: Array<{ command: string }> } };

describe('Extension activation', () => {
    beforeEach(() => {
        sinon.restore();
        (vscodeApi.commands.registerCommand as sinon.SinonStub).resetHistory();
        (vscodeApi.commands.executeCommand as sinon.SinonStub).resetHistory();
        (vscodeApi.lm.registerMcpServerDefinitionProvider as sinon.SinonStub).resetHistory();
        (vscodeApi.workspace.getConfiguration as sinon.SinonStub).returns(new MockWorkspaceConfiguration({}));
        (vscodeApi.window.showErrorMessage as sinon.SinonStub).resolves(undefined);
        (vscodeApi.window.showErrorMessage as sinon.SinonStub).resetHistory();
    });

    afterEach(() => {
        sinon.restore();
        workspace.workspaceFolders = undefined;
        workspace.isTrusted = true;
    });

    /** Activation with a Python setup that fails offline, so nothing touches the network or disk. */
    async function activateWithoutPython(): Promise<vscode.ExtensionContext> {
        sinon.stub(UvPythonManager.prototype, 'ensureReady').rejects(new Error('offline'));
        sinon.stub(PythonEnvironment.prototype, 'ensurePython').resolves(null);
        const context = createMockContext();
        const ext = await import('../extension.js');
        await ext.activate(context);
        return context;
    }

    it('registers exactly the commands contributed in package.json (even when setup fails)', async () => {
        await activateWithoutPython();

        const registered = (vscodeApi.commands.registerCommand as sinon.SinonStub).getCalls().map(c => c.args[0]);
        const contributed = manifest.contributes.commands.map(c => c.command);
        assert.deepStrictEqual([...registered].sort(), [...contributed].sort());
        assert.strictEqual(new Set(registered).size, registered.length, 'a command was registered twice');
    });

    it('disposes everything it creates with the extension and does not register MCP servers without Python', async () => {
        const context = await activateWithoutPython();

        assert.ok(context.subscriptions.some(d => d instanceof UvPythonManager));
        assert.ok(context.subscriptions.some(d => d instanceof PythonEnvironment));
        assert.ok((vscodeApi.lm.registerMcpServerDefinitionProvider as sinon.SinonStub).notCalled);
        const contexts = (vscodeApi.commands.executeCommand as sinon.SinonStub).getCalls()
            .filter(c => c.args[0] === 'setContext');
        assert.ok(contexts.some(c => c.args[1] === 'zoteroMcp.pythonReady' && c.args[2] === false));

        for (const disposable of context.subscriptions) { disposable.dispose(); }
    });

    it('deactivate is safe to call at any time', async () => {
        const ext = await import('../extension.js');
        assert.doesNotThrow(() => ext.deactivate());
    });
});

describe('Claude Code consumer wiring', () => {
    let tmpDir: string;
    let originalConfigDir: string | undefined;
    let configPath: string;
    let context: vscode.ExtensionContext;
    const showInfo = vscodeApi.window.showInformationMessage as sinon.SinonStub;
    const showWarning = vscodeApi.window.showWarningMessage as sinon.SinonStub;

    beforeEach(() => {
        sinon.restore();
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'zotero-mcp-claude-wiring-'));
        originalConfigDir = process.env.CLAUDE_CONFIG_DIR;
        process.env.CLAUDE_CONFIG_DIR = tmpDir;
        configPath = path.join(tmpDir, '.claude.json');
        const folder = path.join(tmpDir, 'workspace');
        fs.mkdirSync(path.join(folder, '.git'), { recursive: true });
        workspace.workspaceFolders = [{ uri: { fsPath: folder } }];
        (vscodeApi.workspace.getConfiguration as sinon.SinonStub).returns(new MockWorkspaceConfiguration({ ncbiEmail: 'me@example.org' }));
        context = createMockContext({ globalStorageUri: Uri.file(path.join(tmpDir, 'storage')) });
        showInfo.resetHistory();
        showWarning.resetHistory();
    });

    afterEach(() => {
        sinon.restore();
        workspace.workspaceFolders = undefined;
        if (originalConfigDir === undefined) {
            delete process.env.CLAUDE_CONFIG_DIR;
        } else {
            process.env.CLAUDE_CONFIG_DIR = originalConfigDir;
        }
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('registers silently on activation and announces it only from explicit setup flows', async () => {
        fs.writeFileSync(configPath, '{}');
        const ext = await import('../extension.js');

        await ext.syncClaudeCodeConfiguration(context, '/managed/venv/bin/python', false);
        assert.ok(showInfo.notCalled);
        assert.ok(fs.readFileSync(configPath, 'utf-8').includes('zotero-keeper'));

        await ext.syncClaudeCodeConfiguration(context, '/new/venv/bin/python', true);
        assert.ok(showInfo.calledOnce);
        assert.match(String(showInfo.firstCall.args[0]), /Claude Code/);
    });

    it('warns an explicit setup flow about an unparsable ~/.claude.json and leaves it alone', async () => {
        fs.writeFileSync(configPath, '{ broken');
        const ext = await import('../extension.js');

        await ext.syncClaudeCodeConfiguration(context, '/managed/venv/bin/python', true);
        assert.ok(showWarning.calledOnce);
        assert.match(String(showWarning.firstCall.args[0]), /not valid JSON/);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), '{ broken');
    });

    it('does nothing when Claude Code has never run', async () => {
        const ext = await import('../extension.js');
        await ext.syncClaudeCodeConfiguration(context, '/managed/venv/bin/python', true);
        assert.ok(showInfo.notCalled && showWarning.notCalled);
        assert.deepStrictEqual(fs.readdirSync(tmpDir).sort(), ['workspace']);
    });
});

describe('harness activation policy', () => {
    const context = { extensionPath: '/extension', extension: { packageJSON: { version: '0.9.0' } } } as unknown as vscode.ExtensionContext;

    beforeEach(() => { sinon.restore(); });
    afterEach(() => {
        sinon.restore();
        workspace.workspaceFolders = undefined;
        workspace.isTrusted = true;
    });

    it('does not install on ordinary activation when the setting is off', async () => {
        const install = sinon.stub(harness, 'installHarnessAssets');
        workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
        workspace.getConfiguration.returns({ get: (_key: string, fallback: unknown) => fallback });
        const ext = await import('../extension.js');
        await ext.installCopilotInstructions(context, 'auto');
        assert.ok(install.notCalled);
    });

    it('installs on activation only when the user opted in', async () => {
        const install = sinon.stub(harness, 'installHarnessAssets')
            .returns({ installed: [], updated: [], preserved: [], unchanged: [] });
        workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
        workspace.getConfiguration.returns({
            get: (key: string, fallback: unknown) => key === 'autoUpdateHarness' ? true : fallback,
        });
        const ext = await import('../extension.js');
        await ext.installCopilotInstructions(context, 'auto');
        assert.ok(install.calledOnce);
    });

    it('does not install hooks into an untrusted workspace even manually', async () => {
        const install = sinon.stub(harness, 'installHarnessAssets');
        workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
        workspace.isTrusted = false;
        const ext = await import('../extension.js');
        await ext.installCopilotInstructions(context, 'manual');
        assert.ok(install.notCalled);
    });

    it('does nothing without an open folder', async () => {
        const install = sinon.stub(harness, 'installHarnessAssets');
        workspace.workspaceFolders = undefined;
        const ext = await import('../extension.js');
        await ext.installCopilotInstructions(context, 'manual');
        assert.ok(install.notCalled);
    });

    it('uses the preservation installer, with the extension version, for an explicit manual request', async () => {
        const install = sinon.stub(harness, 'installHarnessAssets')
            .returns({ installed: [], updated: [], preserved: ['AGENTS.md'], unchanged: [] });
        workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
        const ext = await import('../extension.js');
        await ext.installCopilotInstructions(context, 'manual');
        assert.ok(install.calledOnce);
        assert.strictEqual(install.firstCall.args[2], '0.9.0');
    });

    it('reports installer failures to a manual request instead of throwing', async () => {
        sinon.stub(harness, 'installHarnessAssets').throws(new Error('Invalid harness manifest'));
        workspace.workspaceFolders = [{ uri: { fsPath: '/workspace' } }];
        const showError = vscodeApi.window.showErrorMessage as sinon.SinonStub;
        showError.resolves(undefined);
        showError.resetHistory();
        const ext = await import('../extension.js');
        await assert.doesNotReject(ext.installCopilotInstructions(context, 'manual'));
        assert.ok(String(showError.firstCall.args[0]).includes('Invalid harness manifest'));
    });
});
