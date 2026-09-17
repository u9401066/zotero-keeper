/** Content-addressed workspace harness installation. Never infer ownership from names/headings. */
import * as fs from 'fs';
import * as path from 'path';
import { createHash, randomUUID } from 'crypto';

export const HARNESS_MANIFEST = '.vscode/zotero-mcp-assets.json';
export const HARNESS_PENDING = '.vscode/zotero-mcp-assets.pending.json';
interface Manifest {
    schema: 1;
    extensionVersion: string;
    files: Record<string, string>;
}
export interface HarnessResult {
    installed: string[];
    updated: string[];
    preserved: string[];
    unchanged: string[];
    skipped?: string;
}

function digest(data: Buffer): string {
    return createHash('sha256').update(data).digest('hex');
}

function versionParts(version: string): number[] {
    if (typeof version !== 'string' || !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)
        || !version.split('.').every(p => Number.isSafeInteger(Number(p)))) {
        throw new Error('Harness version must be a stable semantic version.');
    }
    return version.split('.').map(Number);
}

function isOlder(incoming: string, installed: string): boolean {
    const a = versionParts(incoming);
    const b = versionParts(installed);
    for (let i = 0; i < 3; i++) {
        if (a[i] !== b[i]) { return a[i] < b[i]; }
    }
    return false;
}

function safePath(root: string, relative: string): string {
    if (path.isAbsolute(relative) || relative.includes('\\') || relative.includes(':')
        || relative.split('/').some(p => p === '..' || p === '.' || !p)) {
        throw new Error(`Invalid harness path: ${relative}`);
    }
    const parts = relative.split(/[\\/]/);
    let current = root;
    for (const part of parts) {
        current = path.join(current, part);
        // lstat also detects dangling symlinks, unlike existsSync.
        try {
            if (fs.lstatSync(current).isSymbolicLink()) {
                throw new Error(`Harness path is a symbolic link: ${relative}`);
            }
        } catch (error) {
            if ((error as NodeJS.ErrnoException).code !== 'ENOENT') { throw error; }
        }
    }
    return current;
}

/** Source repositories own their harness; an installed extension must not write back into them. */
export function isHarnessSourceWorkspace(root: string): boolean {
    return fs.existsSync(path.join(root, 'vscode-extension', 'scripts', 'sync-copilot-assets.mjs'))
        || (fs.existsSync(path.join(root, 'src', 'pubmed_search'))
            && fs.existsSync(path.join(root, 'pyproject.toml')));
}

function bundleFiles(root: string): Map<string, Buffer> {
    const files = new Map<string, Buffer>();
    const walk = (directory: string, prefix: string): void => {
        for (const entry of fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
            const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
            if (entry.isSymbolicLink()) { throw new Error(`Bundled harness symlink: ${relative}`); }
            const source = path.join(directory, entry.name);
            if (entry.isDirectory()) { walk(source, relative); }
            else if (entry.isFile()) {
                const content = fs.readFileSync(source);
                const existing = files.get(relative);
                if (existing && !existing.equals(content)) {
                    throw new Error(`Conflicting bundled harness: ${relative}`);
                }
                files.set(relative, content);
            }
        }
    };
    for (const owner of ['keeper', 'pubmed-search-mcp']) { walk(path.join(root, owner), ''); }
    return files;
}

/**
 * Existing unknown/edited files and user deletions are preserved, in manual and automatic modes.
 * Unchanged managed files may upgrade; old extension versions cannot downgrade a workspace.
 * Retired assets are left in place for review, never deleted by a prefix-based allowlist.
 */
export function installHarnessAssets(bundleRoot: string, workspaceRoot: string, extensionVersion: string): HarnessResult {
    if (isHarnessSourceWorkspace(workspaceRoot)) {
        return { installed: [], updated: [], preserved: [], unchanged: [], skipped: 'Source repository: edit harness sources and run sync-assets here.' };
    }
    const root = fs.realpathSync(workspaceRoot);
    if (fs.existsSync(safePath(root, HARNESS_PENDING))) {
        return { installed: [], updated: [], preserved: [], unchanged: [], skipped: `Interrupted harness update: review ${HARNESS_PENDING} and its recovery backups before reinstalling. No assets were changed.` };
    }
    const lock = safePath(root, '.vscode/zotero-mcp-assets.lock');
    fs.mkdirSync(path.dirname(lock), { recursive: true });
    let handle: number;
    try { handle = fs.openSync(lock, 'wx'); }
    catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'EEXIST') { throw error; }
        return { installed: [], updated: [], preserved: [], unchanged: [], skipped: 'Harness installation is locked. If no other VS Code window is installing, review .vscode/zotero-mcp-assets.lock before removing the stale lock.' };
    }
    try { return installUnlocked(bundleRoot, root, extensionVersion); }
    finally { fs.closeSync(handle); fs.unlinkSync(lock); }
}

function installUnlocked(bundleRoot: string, workspaceRoot: string, extensionVersion: string): HarnessResult {
    const result: HarnessResult = { installed: [], updated: [], preserved: [], unchanged: [] };
    versionParts(extensionVersion);
    if (isHarnessSourceWorkspace(workspaceRoot)) {
        return { ...result, skipped: 'Source repository: edit harness sources and run sync-assets here.' };
    }
    const root = fs.realpathSync(workspaceRoot);
    const manifestPath = safePath(root, HARNESS_MANIFEST);
    let previous: Manifest = { schema: 1, extensionVersion, files: {} };
    if (fs.existsSync(manifestPath)) {
        // A corrupt/unknown ledger fails before any file is touched.
        previous = JSON.parse(fs.readFileSync(manifestPath, 'utf8')) as Manifest;
        if (!previous || previous.schema !== 1 || !previous.files || typeof previous.files !== 'object'
            || Array.isArray(previous.files)
            || !Object.values(previous.files).every(hash => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash))) {
            throw new Error('Invalid harness manifest; preserve it and review before reinstalling.');
        }
        if (isOlder(extensionVersion, previous.extensionVersion)) {
            return { ...result, skipped: `Newer harness ${previous.extensionVersion} is already installed.` };
        }
        for (const relative of Object.keys(previous.files)) { safePath(root, relative); }
    }
    const files = bundleFiles(bundleRoot);
    const next: Manifest = { schema: 1, extensionVersion, files: { ...previous.files } };
    const changes: AssetChange[] = [];
    // Preflight every destination so a symlink fails before any installation begins.
    for (const relative of files.keys()) { safePath(root, relative); }
    // A skill is one unit: never mix new scripts/references into a custom or edited skill.
    const preservedSkills = new Set<string>();
    const skillRoots = new Set([...files.keys()].map(p => p.match(/^(\.(?:claude|cline|codex)\/skills\/[^/]+)\//)?.[1]).filter((p): p is string => !!p));
    for (const skill of skillRoots) {
        const target = safePath(root, skill);
        const recorded = Object.keys(previous.files).filter(p => p.startsWith(skill + '/'));
        if (!fs.existsSync(target)) {
            if (recorded.length) { preservedSkills.add(skill); }
            continue;
        }
        if (!recorded.length || !fs.statSync(target).isDirectory()) { preservedSkills.add(skill); continue; }
        const inspect = (dir: string, prefix: string): void => {
            for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
                const relative = prefix + '/' + entry.name;
                if (entry.isDirectory()) { inspect(path.join(dir, entry.name), relative); }
                else if (!entry.isFile() || !previous.files[relative]
                    || digest(fs.readFileSync(path.join(dir, entry.name))) !== previous.files[relative]) {
                    preservedSkills.add(skill);
                }
            }
        };
        inspect(target, skill);
        if (recorded.some(p => !fs.existsSync(safePath(root, p)))) { preservedSkills.add(skill); }
    }
    for (const [relative, incoming] of files) {
        if ([...preservedSkills].some(skill => relative.startsWith(skill + '/'))) {
            result.preserved.push(relative); continue;
        }
        const target = safePath(root, relative);
        const hash = digest(incoming);
        const recorded = previous.files[relative];
        if (!fs.existsSync(target)) {
            if (recorded) { result.preserved.push(relative); continue; }
            changes.push({ relative, incoming });
            next.files[relative] = hash;
            result.installed.push(relative);
            continue;
        }
        if (!fs.lstatSync(target).isFile()) { result.preserved.push(relative); continue; }
        const current = fs.readFileSync(target);
        if (current.equals(incoming)) {
            next.files[relative] = hash;
            result.unchanged.push(relative);
        } else if (recorded && digest(current) === recorded) {
            // Same-version bundle divergence isn't an upgrade (e.g. competing development builds).
            if (previous.extensionVersion === extensionVersion) { result.preserved.push(relative); continue; }
            changes.push({ relative, incoming, previous: current, mode: fs.statSync(target).mode });
            next.files[relative] = hash;
            result.updated.push(relative);
        } else { result.preserved.push(relative); }
    }
    const serialized = JSON.stringify(next, null, 2) + '\n';
    if (!fs.existsSync(manifestPath) || fs.readFileSync(manifestPath, 'utf8') !== serialized) {
        changes.push({ relative: HARNESS_MANIFEST, incoming: Buffer.from(serialized),
            previous: fs.existsSync(manifestPath) ? fs.readFileSync(manifestPath) : undefined });
    }
    commitChanges(root, previous.extensionVersion, extensionVersion, changes);
    return result;
}

interface AssetChange {
    relative: string;
    incoming: Buffer;
    previous?: Buffer;
    mode?: number;
}

/** Stage beside the destination: a failed write cannot truncate the installed file. */
function atomicWrite(target: string, content: Buffer, exclusive: boolean, mode?: number): void {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    const temporary = `${target}.${randomUUID()}.tmp`;
    let handle: number | undefined;
    try {
        handle = fs.openSync(temporary, 'wx', mode);
        fs.writeFileSync(handle, content);
        fs.fsyncSync(handle);
        fs.closeSync(handle);
        handle = undefined;
        // link is an atomic no-replace installation; rename atomically replaces a managed file.
        if (exclusive) { fs.linkSync(temporary, target); }
        else { fs.renameSync(temporary, target); }
    } finally {
        if (handle !== undefined) { fs.closeSync(handle); }
        if (fs.existsSync(temporary)) { fs.unlinkSync(temporary); }
    }
}

function matches(root: string, change: AssetChange, expected: Buffer | undefined): boolean {
    const target = safePath(root, change.relative);
    if (!fs.existsSync(target)) { return expected === undefined; }
    return expected !== undefined && fs.lstatSync(target).isFile() && fs.readFileSync(target).equals(expected);
}

/** One recoverable transaction for assets AND ledger. Crashes leave an explicit stop marker. */
function commitChanges(root: string, from: string, to: string, changes: AssetChange[]): void {
    if (!changes.length) { return; }
    const pending = safePath(root, HARNESS_PENDING);
    const journal = changes.map(change => {
        if (!matches(root, change, change.previous)) {
            throw new Error(`Harness changed during planning: ${change.relative}. Re-run after the editor save completes.`);
        }
        let backup: string | undefined;
        if (change.previous !== undefined) {
            backup = `.vscode/zotero-mcp-backups/${from}/${digest(change.previous)}/${change.relative}`;
            const backupPath = safePath(root, backup);
            if (fs.existsSync(backupPath)) {
                if (!fs.lstatSync(backupPath).isFile() || !fs.readFileSync(backupPath).equals(change.previous)) {
                    throw new Error(`Harness recovery backup was modified: ${backup}. No assets were changed.`);
                }
            } else { atomicWrite(backupPath, change.previous, true, change.mode); }
        }
        return { path: change.relative, before: change.previous === undefined ? null : digest(change.previous),
            after: digest(change.incoming), backup };
    });
    atomicWrite(pending, Buffer.from(JSON.stringify({ schema: 1, from, to, files: journal }, null, 2) + '\n'), true);
    const applied: AssetChange[] = [];
    try {
        for (const change of changes) {
            if (!matches(root, change, change.previous)) {
                throw new Error(`Harness changed during update: ${change.relative}.`);
            }
            atomicWrite(safePath(root, change.relative), change.incoming, change.previous === undefined, change.mode);
            applied.push(change);
        }
    } catch (error) {
        let restored = true;
        for (const change of applied.reverse()) {
            try {
                // Never roll back over a user's concurrent edit, even after a failed installation.
                if (!matches(root, change, change.incoming)) { restored = false; continue; }
                const target = safePath(root, change.relative);
                if (change.previous === undefined) { fs.unlinkSync(target); }
                else { atomicWrite(target, change.previous, false, change.mode); }
            } catch { restored = false; }
        }
        if (restored) { fs.unlinkSync(pending); }
        throw new Error(`Harness update failed: ${String(error)} ${restored ? 'Previous assets and ledger restored.' : `Review ${HARNESS_PENDING} and recovery backups; further updates are blocked.`}`);
    }
    fs.unlinkSync(pending);
}
