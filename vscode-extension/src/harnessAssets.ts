/** Content-addressed workspace harness installation. Never infer ownership from names/headings. */
import * as fs from 'fs';
import * as path from 'path';
import { createHash } from 'crypto';

export const HARNESS_MANIFEST = '.vscode/zotero-mcp-assets.json';
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
    if (!/^\d+\.\d+\.\d+$/.test(version)) {
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
    if (path.isAbsolute(relative) || relative.split(/[\\/]/).some(p => p === '..' || !p)) {
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
                if (files.has(relative) && !files.get(relative)!.equals(content)) {
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
        if (previous.schema !== 1 || !previous.files || typeof previous.files !== 'object'
            || Array.isArray(previous.files)
            || !Object.values(previous.files).every(hash => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash))) {
            throw new Error('Invalid harness manifest; preserve it and review before reinstalling.');
        }
        if (isOlder(extensionVersion, previous.extensionVersion)) {
            return { ...result, skipped: `Newer harness ${previous.extensionVersion} is already installed.` };
        }
    }
    const files = bundleFiles(bundleRoot);
    const next: Manifest = { schema: 1, extensionVersion, files: { ...previous.files } };
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
            fs.mkdirSync(path.dirname(target), { recursive: true });
            fs.writeFileSync(target, incoming, { flag: 'wx' });
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
            const backupRelative = `.vscode/zotero-mcp-backups/${previous.extensionVersion}/${recorded}/${relative}`;
            const backup = safePath(root, backupRelative);
            fs.mkdirSync(path.dirname(backup), { recursive: true });
            if (!fs.existsSync(backup)) { fs.writeFileSync(backup, current, { flag: 'wx' }); }
            // Avoid overwriting an editor save that happened during backup creation.
            if (!fs.readFileSync(safePath(root, relative)).equals(current)) {
                result.preserved.push(relative); continue;
            }
            fs.writeFileSync(target, incoming);
            next.files[relative] = hash;
            result.updated.push(relative);
        } else { result.preserved.push(relative); }
    }
    const serialized = JSON.stringify(next, null, 2) + '\n';
    if (!fs.existsSync(manifestPath) || fs.readFileSync(manifestPath, 'utf8') !== serialized) {
        fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
        fs.writeFileSync(manifestPath, serialized);
    }
    return result;
}
