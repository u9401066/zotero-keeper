/**
 * Mock for the 'vscode' module.
 * Provides stubs for all VS Code APIs used by the extension.
 *
 * Usage: import this BEFORE importing any module that depends on 'vscode'.
 * The module cache is patched via register() so that `import * as vscode from 'vscode'`
 * resolves to these mocks.
 */

import * as sinon from 'sinon';

// ─── Event & Disposable ───

export class EventEmitter<T> {
    private listeners: Array<(e: T) => void> = [];
    readonly event = (listener: (e: T) => void) => {
        this.listeners.push(listener);
        return { dispose: () => { this.listeners = this.listeners.filter(l => l !== listener); } };
    };
    fire(data: T): void { this.listeners.forEach(l => l(data)); }
    dispose(): void { this.listeners = []; }
}

export class Disposable {
    constructor(private callOnDispose: () => void) {}
    dispose(): void { this.callOnDispose(); }
    static from(...disposables: { dispose: () => void }[]): Disposable {
        return new Disposable(() => disposables.forEach(d => d.dispose()));
    }
}

// ─── URI ───

export class Uri {
    readonly scheme: string;
    readonly authority: string;
    readonly path: string;
    readonly fsPath: string;
    constructor(scheme: string, authority: string, pathStr: string) {
        this.scheme = scheme;
        this.authority = authority;
        this.path = pathStr;
        this.fsPath = pathStr;
    }
    static file(p: string): Uri { return new Uri('file', '', p); }
    static parse(value: string): Uri { return new Uri('https', '', value); }
    toString(): string { return `${this.scheme}://${this.authority}${this.path}`; }
}

// ─── Status Bar ───

export enum StatusBarAlignment { Left = 1, Right = 2 }

export class MockStatusBarItem {
    text = '';
    tooltip: string | undefined;
    command: string | undefined;
    backgroundColor: ThemeColor | undefined;
    show = sinon.stub();
    hide = sinon.stub();
    dispose = sinon.stub();
}

// ─── ThemeColor ───

export class ThemeColor {
    constructor(public readonly id: string) {}
}

// ─── QuickPick ───

export enum QuickPickItemKind { Separator = -1, Default = 0 }

// ─── Configuration ───

export class MockWorkspaceConfiguration {
    private data: Record<string, unknown>;
    constructor(data: Record<string, unknown> = {}) { this.data = data; }
    get<T>(key: string, defaultValue?: T): T {
        return (this.data[key] as T) ?? (defaultValue as T);
    }
    update = sinon.stub().resolves();
    has(key: string): boolean { return key in this.data; }
    inspect = sinon.stub().returns(undefined);
}

// ─── ExtensionContext ───

export function createMockContext(overrides: Partial<MockExtensionContext> = {}): MockExtensionContext {
    return {
        subscriptions: [],
        extensionPath: '/mock/extension',
        globalStorageUri: Uri.file('/mock/storage'),
        globalState: {
            get: sinon.stub().returns(undefined),
            update: sinon.stub().resolves(),
            keys: sinon.stub().returns([]),
            setKeysForSync: sinon.stub(),
        },
        extension: {
            packageJSON: { version: '0.5.25' },
        },
        ...overrides,
    } as MockExtensionContext;
}

export interface MockExtensionContext {
    subscriptions: { dispose: () => void }[];
    extensionPath: string;
    globalStorageUri: Uri;
    globalState: {
        get: sinon.SinonStub;
        update: sinon.SinonStub;
        keys: sinon.SinonStub;
        setKeysForSync: sinon.SinonStub;
    };
    extension: { packageJSON: Record<string, unknown> };
}

// ─── McpStdioServerDefinition ───

export class McpStdioServerDefinition {
    constructor(
        public label: string,
        public command: string,
        public args: string[],
        public env?: Record<string, string>,
        public version?: string,
    ) {}
}

// ─── Namespace stubs ───

export const window = {
    createStatusBarItem: sinon.stub().callsFake(() => new MockStatusBarItem()),
    createOutputChannel: sinon.stub().returns({
        appendLine: sinon.stub(),
        append: sinon.stub(),
        show: sinon.stub(),
        dispose: sinon.stub(),
    }),
    showInformationMessage: sinon.stub().resolves(undefined),
    showWarningMessage: sinon.stub().resolves(undefined),
    showErrorMessage: sinon.stub().resolves(undefined),
    showQuickPick: sinon.stub().resolves(undefined),
    createWebviewPanel: sinon.stub().returns({
        webview: { html: '' },
        dispose: sinon.stub(),
    }),
    withProgress: sinon.stub().callsFake(async (_opts: unknown, task: (progress: unknown) => Promise<unknown>) => {
        const progress = { report: sinon.stub() };
        return task(progress);
    }),
};

export const workspace = {
    getConfiguration: sinon.stub().callsFake((_section?: string) => {
        return new MockWorkspaceConfiguration();
    }),
    workspaceFolders: undefined as unknown[] | undefined,
};

export const commands = {
    registerCommand: sinon.stub().callsFake((_cmd: string, _cb: (...args: unknown[]) => unknown) => {
        return new Disposable(() => {});
    }),
    executeCommand: sinon.stub().resolves(),
};

export const extensions = {
    getExtension: sinon.stub().returns(undefined),
};

export const env = {
    openExternal: sinon.stub().resolves(true),
};

export const lm = {
    registerMcpServerDefinitionProvider: sinon.stub().returns(new Disposable(() => {})),
};

export enum ProgressLocation {
    SourceControl = 1,
    Window = 10,
    Notification = 15,
}

export enum ViewColumn {
    Active = -1,
    Beside = -2,
    One = 1,
    Two = 2,
}

export enum ConfigurationTarget {
    Global = 1,
    Workspace = 2,
    WorkspaceFolder = 3,
}

// ─── Reset all stubs ───

export function resetAllMocks(): void {
    sinon.restore();
    // Re-create stubs on namespaces
    window.createStatusBarItem.resetHistory();
    window.createOutputChannel.resetHistory();
    window.showInformationMessage.resetHistory();
    window.showWarningMessage.resetHistory();
    window.showErrorMessage.resetHistory();
    window.showQuickPick.resetHistory();
    window.withProgress.resetHistory();
    workspace.getConfiguration.resetHistory();
    commands.registerCommand.resetHistory();
    commands.executeCommand.resetHistory();
    extensions.getExtension.resetHistory();
    lm.registerMcpServerDefinitionProvider.resetHistory();
}
