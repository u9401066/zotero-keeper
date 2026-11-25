/**
 * Claude Code MCP Configuration Manager
 *
 * Registers Zotero Keeper and PubMed Search MCP for Claude Code (CLI and IDE
 * extensions), which reads stdio servers from its global state file:
 *
 *   $CLAUDE_CONFIG_DIR/.claude.json when set, otherwise <home>/.claude.json
 *
 *   - user scope:  top-level `"mcpServers": { NAME: {...} }`
 *   - local scope: `"projects": { "<project path>": { "mcpServers": { NAME: {...} } } }`
 *   - project scope (`.mcp.json` in the repository) is never written: it is
 *     committed, so it would publish a machine-specific interpreter path, the
 *     NCBI e-mail and API keys, and every collaborator must approve it.
 *
 * `zoteroMcp.claudeCodeMcpScope` selects where:
 *   - "local" (default): per workspace folder, keyed exactly like Claude Code
 *     keys a project (the folder's git root, forward slashes on Windows).
 *     PUBMED_WORKSPACE_DIR names one workspace, and a per-project slot is the
 *     only place where it is never wrong: windows of different workspaces do
 *     not overwrite each other (Codex and Cline only have one global file), and
 *     hand-made user-scope entries stay untouched while the local entry takes
 *     precedence inside the project.
 *   - "user": one global registration, without PUBMED_WORKSPACE_DIR so it is
 *     never pinned to whichever workspace synced last (PubMed then falls back to
 *     the session's working directory when that looks like a project root).
 *   - "off": register nothing and withdraw what this extension registered.
 *
 * `.claude.json` is Claude Code's own state file (account, projects, caches)
 * and Claude Code rewrites it constantly, so this writer:
 *   - never creates it (Claude Code not run yet → nothing to do) and never
 *     rewrites a file it cannot parse, decode or reinterpret;
 *   - takes Claude Code's own lock (the `<file>.lock` directory of the
 *     proper-lockfile protocol) and never breaks a lock it does not hold;
 *   - re-reads the file right before the atomic rename and starts over if it
 *     changed meanwhile;
 *   - changes only the entries it owns. Ownership is content-addressed (a
 *     SHA-256 ledger in the extension's global storage), so an entry the user
 *     wrote under the same name, or a managed entry the user edited, is
 *     preserved verbatim; every other key is carried through unchanged;
 *   - keeps a rolling backup (`<file>.zotero-mcp.bak`) of the bytes it replaced
 *     and keeps the file's indentation, line endings, BOM and final newline.
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { createHash } from 'crypto';
import { PUBMED_SEARCH_ENTRYPOINT } from './pubmedSearchPackage.js';
import { buildPubmedEnv, buildZoteroEnv, writeFileAtomic } from './mcpServerConfig.js';

const ZOTERO_SERVER_KEY = 'zotero-keeper';
const PUBMED_SERVER_KEY = 'pubmed-search-mcp';
const MANAGED_SERVERS = [ZOTERO_SERVER_KEY, PUBMED_SERVER_KEY] as const;
type ManagedServer = typeof MANAGED_SERVERS[number];

export type ClaudeCodeScope = 'local' | 'user' | 'off';
const SCOPES: readonly string[] = ['local', 'user', 'off'];

const LEDGER_FILE = 'claude-code-mcp-ledger.json';
const BACKUP_SUFFIX = '.zotero-mcp.bak';
/** Hashes remembered per slot, so a write that failed after being recorded never orphans the previous entry. */
const HASHES_PER_SLOT = 5;
/** Read-merge-write attempts when the file keeps changing under us. */
const MAX_ATTEMPTS = 3;

type JsonObject = Record<string, unknown>;

interface ClaudeStdioServerEntry {
    type: 'stdio';
    command: string;
    args: string[];
    env: Record<string, string>;
}

/** A server slot: user scope when `project` is undefined, otherwise `projects[project]`. */
interface Slot {
    project?: string;
    server: ManagedServer;
}

export interface ClaudeCodeSyncResult {
    status: 'updated' | 'unchanged' | 'not-detected' | 'invalid' | 'busy' | 'conflict' | 'failed';
    /** The configured scope (the raw value when it is not a known scope). */
    scope: string;
    configPath: string;
    /** Slots created or refreshed, e.g. `user zotero-keeper` or `local[g:/work] pubmed-search-mcp`. */
    written: string[];
    removed: string[];
    /** Slots holding an entry this extension does not own (user-defined, or a managed entry the user edited). */
    preserved: string[];
    message?: string;
}

type ConfigReader = Pick<vscode.WorkspaceConfiguration, 'get'>;
type StorageContext = Pick<vscode.ExtensionContext, 'globalStorageUri'>;

/** Content the writer must not reinterpret: reported, never "repaired". */
class ConfigRefusedError extends Error {}
/** The file changed between our read and our rename. */
class ConcurrentModificationError extends Error {}

const testSeams: {
    lockRetryDelaysMs: number[];
    /** Runs immediately before the stale-read check of each commit attempt. */
    beforeCommitCheck?: (target: string) => void;
} = { lockRetryDelaysMs: [20, 40, 80, 160, 320, 640, 1000] };

// ─── Locations ───────────────────────────────────────────────────────────────

/** `$CLAUDE_CONFIG_DIR/.claude.json` when set, otherwise `<home>/.claude.json`. */
export function getClaudeConfigPath(): string {
    const override = process.env.CLAUDE_CONFIG_DIR?.trim();
    return path.join(override || os.homedir(), '.claude.json');
}

/** Claude Code creates its state file on first launch; the extension never creates it. */
export function isClaudeCodeAvailable(): boolean {
    try {
        return fs.statSync(getClaudeConfigPath()).isFile();
    } catch {
        return false;
    }
}

/** The configured scope, or undefined for a value this version does not know (then nothing is touched). */
export function getClaudeCodeScope(config: ConfigReader): ClaudeCodeScope | undefined {
    const value = config.get<string>('claudeCodeMcpScope', 'local');
    return SCOPES.includes(value) ? value as ClaudeCodeScope : undefined;
}

/**
 * The key Claude Code files a session's local-scope settings under: the git
 * root containing `folder` (else the folder itself), with forward slashes on
 * Windows. The drive letter is kept as given; VS Code reports it in lower case,
 * exactly like the Claude Code extension it launches.
 */
export function getClaudeProjectKey(folder: string, platform: NodeJS.Platform = process.platform): string {
    const paths = platform === 'win32' ? path.win32 : path.posix;
    const resolved = paths.resolve(folder);
    const root = findGitRoot(resolved, paths) ?? resolved;
    return platform === 'win32' ? root.replace(/\\/g, '/') : root;
}

function findGitRoot(start: string, paths: path.PlatformPath): string | undefined {
    for (let dir = start; ; dir = paths.dirname(dir)) {
        if (fs.existsSync(paths.join(dir, '.git'))) { return dir; }
        if (paths.dirname(dir) === dir) { return undefined; }
    }
}

/** Identity of a project key: Windows paths compare case- and separator-insensitively. */
function projectIdentity(key: string, platform: NodeJS.Platform): string {
    const unified = key.normalize('NFC');
    return platform === 'win32'
        ? unified.replace(/\\/g, '/').replace(/(?<=.)\/+$/, '').toLowerCase()
        : unified.replace(/(?<=.)\/+$/, '');
}

/**
 * Existing `projects` keys naming the same directory (a CLI started from a
 * shell may have recorded `G:/x` next to the IDE's `g:/x`); the canonical key
 * when the project is not known yet.
 */
function matchingProjectKeys(projects: unknown, canonical: string, platform: NodeJS.Platform): string[] {
    if (!isPlainObject(projects)) { return [canonical]; }
    const identity = projectIdentity(canonical, platform);
    const matches = Object.keys(projects).filter(key => projectIdentity(key, platform) === identity);
    return matches.length > 0 ? matches : [canonical];
}

function describeSlot(slot: Slot): string {
    return slot.project === undefined ? `user ${slot.server}` : `local[${slot.project}] ${slot.server}`;
}

// ─── Entries ─────────────────────────────────────────────────────────────────

function buildEntry(
    server: ManagedServer,
    pythonPath: string,
    config: ConfigReader,
    workspaceFolder?: string,
): ClaudeStdioServerEntry {
    return server === ZOTERO_SERVER_KEY
        ? { type: 'stdio', command: pythonPath, args: ['-m', 'zotero_mcp'], env: buildZoteroEnv(config) }
        : { type: 'stdio', command: pythonPath, args: ['-m', PUBMED_SEARCH_ENTRYPOINT], env: buildPubmedEnv(config, workspaceFolder) };
}

/** Key-order independent JSON, so Claude Code reordering an entry does not change its identity. */
function canonicalJson(value: unknown): string {
    if (Array.isArray(value)) {
        return `[${value.map(canonicalJson).join(',')}]`;
    }
    if (isPlainObject(value)) {
        return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
    }
    return JSON.stringify(value) ?? 'null';
}

function sha256(data: string | Uint8Array): string {
    return createHash('sha256').update(data).digest('hex');
}

function entryHash(entry: unknown): string {
    return sha256(canonicalJson(entry));
}

/** Shape `claude mcp add --scope local` gives a project Claude Code has not opened yet. */
function defaultProjectConfig(): JsonObject {
    return {
        allowedTools: [],
        mcpContextUris: [],
        mcpServers: {},
        enabledMcpjsonServers: [],
        disabledMcpjsonServers: [],
        hasTrustDialogAccepted: false,
        hasClaudeMdExternalIncludesApproved: false,
        hasClaudeMdExternalIncludesWarningShown: false,
    };
}

// ─── JSON document ───────────────────────────────────────────────────────────

function isPlainObject(value: unknown): value is JsonObject {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasOwn(object: JsonObject, key: string): boolean {
    return Object.prototype.hasOwnProperty.call(object, key);
}

/** Plain assignment would treat a `__proto__` key specially; config keys are data. */
function setOwn(object: JsonObject, key: string, value: unknown): void {
    Object.defineProperty(object, key, { value, enumerable: true, writable: true, configurable: true });
}

interface JsonFormat {
    bom: boolean;
    eol: '\n' | '\r\n';
    /** undefined for a single-line (compact) document. */
    indent: string | undefined;
    finalNewline: boolean;
}

function detectFormat(text: string): JsonFormat {
    const bom = text.startsWith('\uFEFF');
    const body = bom ? text.slice(1) : text;
    const multiline = /\n/.test(body.trimEnd());
    return {
        bom,
        eol: body.includes('\r\n') ? '\r\n' : '\n',
        indent: multiline ? body.match(/\n([ \t]+)\S/)?.[1] ?? '  ' : undefined,
        finalNewline: body.endsWith('\n'),
    };
}

function serialize(document: JsonObject, format: JsonFormat): string {
    // JSON.stringify escapes newlines inside strings, so every raw "\n" is structural.
    let text = JSON.stringify(document, null, format.indent);
    if (format.eol === '\r\n') { text = text.replace(/\n/g, '\r\n'); }
    if (format.finalNewline) { text += format.eol; }
    return (format.bom ? '\uFEFF' : '') + text;
}

interface Snapshot {
    /** The file actually replaced (a symlinked config is written through to its target). */
    target: string;
    bytes: Buffer;
    digest: string;
    document: JsonObject;
    format: JsonFormat;
}

function readSnapshot(configPath: string): Snapshot {
    const target = fs.realpathSync(configPath);
    const bytes = fs.readFileSync(target);
    const text = bytes.toString('utf-8');
    if (!Buffer.from(text, 'utf-8').equals(bytes)) {
        throw new ConfigRefusedError('is not valid UTF-8');
    }
    const format = detectFormat(text);
    let document: unknown;
    try {
        document = JSON.parse(format.bom ? text.slice(1) : text);
    } catch (error) {
        throw new ConfigRefusedError(`is not valid JSON (${error instanceof Error ? error.message : String(error)})`);
    }
    if (!isPlainObject(document)) {
        throw new ConfigRefusedError('does not hold a JSON object');
    }
    return { target, bytes, digest: sha256(bytes), document, format };
}

/**
 * The `mcpServers` object of a slot. Missing containers are created only when
 * `create` is set (a new project gets Claude Code's default shape); a container
 * of any other type is refused rather than replaced.
 */
function serversAt(document: JsonObject, project: string | undefined, create: true): JsonObject;
function serversAt(document: JsonObject, project: string | undefined, create: false): JsonObject | undefined;
function serversAt(document: JsonObject, project: string | undefined, create: boolean): JsonObject | undefined {
    let owner = document;
    if (project !== undefined) {
        if (!hasOwn(document, 'projects')) {
            if (!create) { return undefined; }
            setOwn(document, 'projects', {});
        }
        const projects = document.projects;
        if (!isPlainObject(projects)) {
            throw new ConfigRefusedError('has a "projects" value that is not an object');
        }
        if (!hasOwn(projects, project)) {
            if (!create) { return undefined; }
            setOwn(projects, project, defaultProjectConfig());
        }
        const entry = projects[project];
        if (!isPlainObject(entry)) {
            throw new ConfigRefusedError(`has a project entry for ${project} that is not an object`);
        }
        owner = entry;
    }
    if (!hasOwn(owner, 'mcpServers')) {
        if (!create) { return undefined; }
        setOwn(owner, 'mcpServers', {});
    }
    const servers = owner.mcpServers;
    if (!isPlainObject(servers)) {
        throw new ConfigRefusedError(`has ${project === undefined ? 'a top-level' : `a ${project}`} "mcpServers" value that is not an object`);
    }
    return servers;
}

function entryAt(document: JsonObject, slot: Slot): unknown {
    const servers = serversAt(document, slot.project, false);
    return servers && hasOwn(servers, slot.server) ? servers[slot.server] : undefined;
}

// ─── Ownership ledger ────────────────────────────────────────────────────────

interface Ledger {
    version: 1;
    /** slot id → hashes of entries this extension wrote there (newest last). */
    entries: Record<string, string[]>;
}

function slotId(configId: string, slot: Slot): string {
    return JSON.stringify([configId, slot.project ?? null, slot.server]);
}

function getLedgerPath(context: StorageContext): string {
    return path.join(context.globalStorageUri.fsPath, LEDGER_FILE);
}

/** A missing or damaged ledger owns nothing: existing entries are then preserved, never claimed. */
function readLedger(ledgerPath: string): Ledger {
    let raw: string;
    try {
        raw = fs.readFileSync(ledgerPath, 'utf-8');
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'ENOENT') { return { version: 1, entries: {} }; }
        throw error;
    }
    try {
        const parsed: unknown = JSON.parse(raw);
        if (isPlainObject(parsed) && parsed.version === 1 && isPlainObject(parsed.entries)) {
            const entries: Record<string, string[]> = {};
            for (const [id, hashes] of Object.entries(parsed.entries)) {
                if (Array.isArray(hashes)) { entries[id] = hashes.filter((h): h is string => typeof h === 'string'); }
            }
            return { version: 1, entries };
        }
    } catch {
        // fall through
    }
    console.warn(`Ignoring unreadable Claude Code ownership ledger: ${ledgerPath}`);
    return { version: 1, entries: {} };
}

function writeLedger(ledgerPath: string, ledger: Ledger): void {
    writeFileAtomic(ledgerPath, JSON.stringify(ledger, null, 2) + '\n');
}

function ownedSlots(ledger: Ledger, configId: string): Slot[] {
    const slots: Slot[] = [];
    for (const id of Object.keys(ledger.entries)) {
        try {
            const [config, project, server] = JSON.parse(id) as [unknown, unknown, unknown];
            if (config === configId
                && (project === null || typeof project === 'string')
                && (MANAGED_SERVERS as readonly unknown[]).includes(server)) {
                slots.push({ project: project ?? undefined, server: server as ManagedServer });
            }
        } catch {
            // not one of ours
        }
    }
    return slots;
}

// ─── Planning ────────────────────────────────────────────────────────────────

interface Desired {
    slot: Slot;
    entry: ClaudeStdioServerEntry;
}

interface Changes {
    written: Slot[];
    removed: Slot[];
    preserved: Slot[];
    /** slot id → hash, recorded before the file is replaced. */
    recorded: Map<string, string>;
    /** slot ids dropped from the ledger after the file is replaced. */
    forgotten: string[];
}

/** Apply the desired state to `document` in place, touching only owned or empty slots. */
function applyChanges(
    document: JsonObject,
    ledger: Ledger,
    configId: string,
    desired: Desired[],
    shouldWithdraw: (slot: Slot) => boolean,
): Changes {
    const changes: Changes = { written: [], removed: [], preserved: [], recorded: new Map(), forgotten: [] };
    const owns = (slot: Slot, entry: unknown): boolean =>
        (ledger.entries[slotId(configId, slot)] ?? []).includes(entryHash(entry));
    const wanted = new Set(desired.map(d => slotId(configId, d.slot)));

    for (const { slot, entry } of desired) {
        const current = entryAt(document, slot);
        if (current !== undefined && canonicalJson(current) === canonicalJson(entry)) { continue; }
        if (current !== undefined && !owns(slot, current)) {
            changes.preserved.push(slot);
            continue;
        }
        serversAt(document, slot.project, true)[slot.server] = entry;
        changes.written.push(slot);
        changes.recorded.set(slotId(configId, slot), entryHash(entry));
    }

    for (const slot of ownedSlots(ledger, configId)) {
        const id = slotId(configId, slot);
        if (wanted.has(id) || !shouldWithdraw(slot)) { continue; }
        const servers = serversAt(document, slot.project, false);
        const current = servers && hasOwn(servers, slot.server) ? servers[slot.server] : undefined;
        if (servers === undefined || current === undefined) {
            changes.forgotten.push(id);
        } else if (!owns(slot, current)) {
            changes.preserved.push(slot);
        } else {
            delete servers[slot.server];
            changes.removed.push(slot);
            changes.forgotten.push(id);
        }
    }

    return changes;
}

// ─── Lock ────────────────────────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Claude Code serializes its own writes with proper-lockfile, whose lock is
 * the directory `<file>.lock` created by an atomic mkdir. Taking the same lock
 * keeps our read-merge-write from interleaving with Claude Code's. A lock held
 * elsewhere is waited for, never removed.
 */
async function acquireLock(lockPath: string): Promise<boolean> {
    for (let attempt = 0; ; attempt++) {
        try {
            fs.mkdirSync(lockPath);
            return true;
        } catch (error) {
            if ((error as NodeJS.ErrnoException).code !== 'EEXIST') { throw error; }
        }
        if (attempt >= testSeams.lockRetryDelaysMs.length) { return false; }
        await delay(testSeams.lockRetryDelaysMs[attempt]);
    }
}

function releaseLock(lockPath: string): void {
    try {
        fs.rmdirSync(lockPath);
    } catch (error) {
        console.error(`Failed to release ${lockPath}:`, error);
    }
}

// ─── Synchronization ─────────────────────────────────────────────────────────

interface SyncRequest {
    scope: ClaudeCodeScope;
    pythonPath: string;
    config: ConfigReader;
    enabled: Record<ManagedServer, boolean>;
    folders: string[];
    configPath: string;
    ledgerPath: string;
}

interface CommitOutcome {
    status: 'updated' | 'unchanged';
    changes: Changes;
}

function commitOnce(request: SyncRequest): CommitOutcome {
    const { scope, configPath, ledgerPath, enabled } = request;
    const snapshot = readSnapshot(configPath);
    const document = snapshot.document;
    const configId = path.resolve(configPath);
    const ledger = readLedger(ledgerPath);

    const desired: Desired[] = [];
    const currentProjects = new Set<string>();
    if (scope === 'user') {
        for (const server of MANAGED_SERVERS) {
            if (enabled[server]) { desired.push({ slot: { server }, entry: buildEntry(server, request.pythonPath, request.config) }); }
        }
    } else if (scope === 'local') {
        for (const folder of request.folders) {
            for (const project of matchingProjectKeys(document.projects, getClaudeProjectKey(folder), process.platform)) {
                // Two folders of one repository share a project: the first folder wins.
                if (currentProjects.has(project)) { continue; }
                currentProjects.add(project);
                for (const server of MANAGED_SERVERS) {
                    if (enabled[server]) {
                        desired.push({ slot: { project, server }, entry: buildEntry(server, request.pythonPath, request.config, folder) });
                    }
                }
            }
        }
    }

    // Registrations of other workspaces stay until that workspace is opened again;
    // a scope change or "off" withdraws every registration this extension owns.
    const shouldWithdraw = (slot: Slot): boolean => {
        if (scope === 'off') { return true; }
        if (slot.project === undefined) { return scope !== 'user' || !enabled[slot.server]; }
        if (scope !== 'local') { return true; }
        return currentProjects.has(slot.project) && !enabled[slot.server];
    };

    const changes = applyChanges(document, ledger, configId, desired, shouldWithdraw);

    if (changes.written.length === 0 && changes.removed.length === 0) {
        if (changes.forgotten.length > 0) {
            for (const id of changes.forgotten) { delete ledger.entries[id]; }
            writeLedger(ledgerPath, ledger);
        }
        return { status: 'unchanged', changes };
    }

    // Record ownership first: if the replacement then fails, the old and the
    // new entry are both still recognized as ours.
    if (changes.recorded.size > 0) {
        for (const [id, hash] of changes.recorded) {
            const hashes = (ledger.entries[id] ?? []).filter(h => h !== hash);
            ledger.entries[id] = [...hashes, hash].slice(-HASHES_PER_SLOT);
        }
        writeLedger(ledgerPath, ledger);
    }

    writeFileAtomic(`${configPath}${BACKUP_SUFFIX}`, snapshot.bytes);
    writeFileAtomic(snapshot.target, serialize(document, snapshot.format), {
        beforeRename: () => {
            testSeams.beforeCommitCheck?.(snapshot.target);
            if (sha256(fs.readFileSync(snapshot.target)) !== snapshot.digest) {
                throw new ConcurrentModificationError(`${configPath} changed while it was being updated`);
            }
        },
    });

    if (changes.forgotten.length > 0) {
        for (const id of changes.forgotten) { delete ledger.entries[id]; }
        writeLedger(ledgerPath, ledger);
    }
    return { status: 'updated', changes };
}

async function syncNow(context: StorageContext, pythonPath: string, scopeOverride?: ClaudeCodeScope): Promise<ClaudeCodeSyncResult> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const configuredScope = config.get<string>('claudeCodeMcpScope', 'local');
    const scope = scopeOverride ?? getClaudeCodeScope(config);
    const configPath = getClaudeConfigPath();
    const result = (status: ClaudeCodeSyncResult['status'], extra: Partial<ClaudeCodeSyncResult> = {}): ClaudeCodeSyncResult => ({
        status, scope: scope ?? configuredScope, configPath, written: [], removed: [], preserved: [], ...extra,
    });

    if (scope === undefined) {
        return result('failed', { message: `Unknown zoteroMcp.claudeCodeMcpScope "${configuredScope}"; Claude Code configuration left unchanged` });
    }
    if (!isClaudeCodeAvailable()) {
        return result('not-detected');
    }
    if (scope !== 'off' && !pythonPath) {
        return result('failed', { message: 'No Python interpreter resolved; Claude Code configuration left unchanged' });
    }

    const request: SyncRequest = {
        scope,
        pythonPath,
        config,
        enabled: {
            [ZOTERO_SERVER_KEY]: config.get<boolean>('enableZoteroKeeper', true),
            [PUBMED_SERVER_KEY]: config.get<boolean>('enablePubmedSearch', true),
        },
        folders: (vscode.workspace.workspaceFolders ?? []).map(folder => folder.uri.fsPath),
        configPath,
        ledgerPath: getLedgerPath(context),
    };

    const lockPath = `${configPath}.lock`;
    let locked = false;
    try {
        locked = await acquireLock(lockPath);
        if (!locked) {
            return result('busy', { message: `${lockPath} is held by another process; Claude Code configuration left unchanged` });
        }
        for (let attempt = 1; ; attempt++) {
            try {
                const { status, changes } = commitOnce(request);
                return result(status, {
                    written: changes.written.map(describeSlot),
                    removed: changes.removed.map(describeSlot),
                    preserved: changes.preserved.map(describeSlot),
                });
            } catch (error) {
                if (!(error instanceof ConcurrentModificationError) || attempt >= MAX_ATTEMPTS) { throw error; }
            }
        }
    } catch (error) {
        if (error instanceof ConfigRefusedError) {
            return result('invalid', { message: `${configPath} ${error.message}; it was left unchanged` });
        }
        if (error instanceof ConcurrentModificationError) {
            return result('conflict', { message: `${error.message}; it was left unchanged` });
        }
        return result('failed', { message: error instanceof Error ? error.message : String(error) });
    } finally {
        if (locked) { releaseLock(lockPath); }
    }
}

let queue: Promise<unknown> = Promise.resolve();

/** Serialize all writers of this extension host; each run re-reads the file. */
function enqueue(task: () => Promise<ClaudeCodeSyncResult>): Promise<ClaudeCodeSyncResult> {
    const run = queue.then(task);
    queue = run.catch(() => undefined);
    return run;
}

/**
 * Register, refresh or withdraw the managed servers according to the current
 * settings. Never throws; the result says what happened.
 */
export function syncClaudeCodeMcpServers(context: StorageContext, pythonPath: string): Promise<ClaudeCodeSyncResult> {
    return enqueue(() => syncNow(context, pythonPath));
}

/** Withdraw every registration this extension owns (user-made entries stay). */
export function removeClaudeCodeMcpServers(context: StorageContext): Promise<ClaudeCodeSyncResult> {
    return enqueue(() => syncNow(context, '', 'off'));
}

// Re-export internals for unit testing.
export const __test__ = {
    seams: testSeams,
    canonicalJson,
    detectFormat,
    serialize,
    matchingProjectKeys,
    getLedgerPath,
    backupSuffix: BACKUP_SUFFIX,
};
