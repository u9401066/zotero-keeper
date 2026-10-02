/**
 * Codex MCP Configuration Manager
 *
 * Automatically configures Zotero Keeper and PubMed Search MCP servers in
 * Codex CLI's ~/.codex/config.toml so Codex users don't need to manually set
 * up MCP servers.
 *
 * Codex config file location:
 *   - Honors $CODEX_HOME if set
 *   - Otherwise: <home>/.codex/config.toml
 *
 * Format reference: https://developers.openai.com/codex/config-reference
 *
 *   [mcp_servers.NAME]
 *   command = "..."
 *   args = ["...", "..."]
 *
 *   [mcp_servers.NAME.env]
 *   KEY = "value"
 *
 * Strategy: We do NOT parse the entire TOML file (would lose user comments
 * and other tables on round-trip). Instead, we detect/replace exactly the
 * `[mcp_servers.zotero-keeper]` and `[mcp_servers.pubmed-search-mcp]`
 * blocks via line-based section scanning. This preserves all unrelated
 * user content untouched.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as os from 'os';
import * as fs from 'fs';
import { PUBMED_SEARCH_ENTRYPOINT } from './pubmedSearchPackage.js';
import { buildPubmedEnv, buildZoteroEnv, getPrimaryWorkspaceFolder, writeFileAtomic } from './mcpServerConfig.js';

const ZOTERO_SERVER_KEY = 'zotero-keeper';
const PUBMED_SERVER_KEY = 'pubmed-search-mcp';

// Headers we manage. We treat both `[mcp_servers.NAME]` and any subtable
// `[mcp_servers.NAME.<...>]` (e.g. `.env`, `.tools.foo`) as belonging to the
// same managed block.
function blockHeaderPattern(serverKey: string): RegExp {
    // ^\s*\[\s*mcp_servers\.<key>(?:\..*)?\s*\]\s*$
    const escapedKey = serverKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`^\\s*\\[\\s*mcp_servers\\.${escapedKey}(?:\\.[^\\]]+)?\\s*\\]\\s*$`);
}

function anyTableHeaderPattern(): RegExp {
    return /^\s*\[\s*[^\]]+\s*\]\s*$/;
}

interface CodexServerSpec {
    command: string;
    args: string[];
    env: Record<string, string>;
}

/**
 * Resolve Codex home directory.  Honors $CODEX_HOME if set, otherwise
 * falls back to <homedir>/.codex .
 */
export function getCodexHome(): string {
    const override = process.env.CODEX_HOME;
    if (override && override.trim()) {
        return override.trim();
    }
    return path.join(os.homedir(), '.codex');
}

export function getCodexConfigPath(): string {
    return path.join(getCodexHome(), 'config.toml');
}

/**
 * Heuristic: Codex CLI is "installed" if ~/.codex exists (created by `codex login`
 * or first run) OR if the user explicitly opted in via the `installCodexConfig`
 * extension setting.
 */
export function isCodexAvailable(): boolean {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    if (config.get<boolean>('installCodexConfig', false)) {
        return true;
    }
    try {
        return fs.existsSync(getCodexHome());
    } catch {
        return false;
    }
}

function escapeTomlString(value: string): string {
    // TOML basic strings: backslash and double-quote require escaping and all
    // other control characters (U+0000-U+001F, U+007F) are forbidden raw.
    // Escaping backslashes also keeps Windows paths like `C:\Users\...` intact.
    return value
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
        .replace(/\t/g, '\\t')
        // eslint-disable-next-line no-control-regex
        .replace(/[\u0000-\u001f\u007f]/g, ch => `\\u${ch.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

function renderArgs(args: string[]): string {
    return '[' + args.map(a => `"${escapeTomlString(a)}"`).join(', ') + ']';
}

function renderManagedBlock(serverKey: string, spec: CodexServerSpec): string {
    const lines: string[] = [];
    lines.push(`[mcp_servers.${serverKey}]`);
    lines.push(`command = "${escapeTomlString(spec.command)}"`);
    lines.push(`args = ${renderArgs(spec.args)}`);

    const envKeys = Object.keys(spec.env).sort();
    if (envKeys.length > 0) {
        lines.push('');
        lines.push(`[mcp_servers.${serverKey}.env]`);
        for (const key of envKeys) {
            lines.push(`${key} = "${escapeTomlString(spec.env[key])}"`);
        }
    }

    return lines.join('\n') + '\n';
}

/**
 * Remove all lines belonging to the managed server block (the `[mcp_servers.NAME]`
 * table and any `[mcp_servers.NAME.subtable]`).  Returns the stripped text and
 * a flag indicating whether anything was removed.
 */
function stripManagedBlock(content: string, serverKey: string): { content: string; removed: boolean } {
    const lines = content.split(/\r?\n/);
    const headerRe = blockHeaderPattern(serverKey);
    const anyHeader = anyTableHeaderPattern();

    const out: string[] = [];
    let removed = false;
    let inManaged = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (inManaged) {
            if (headerRe.test(line)) {
                // Still inside our managed family of subtables
                continue;
            }
            if (anyHeader.test(line)) {
                // Reached an unrelated table header — exit managed block
                inManaged = false;
                out.push(line);
                continue;
            }
            // Body line of managed block: drop
            removed = true;
            continue;
        }

        if (headerRe.test(line)) {
            inManaged = true;
            removed = true;
            // Drop trailing blank line(s) immediately preceding the managed
            // block to avoid accumulating blank lines on each rewrite.
            while (out.length > 0 && out[out.length - 1].trim() === '') {
                out.pop();
            }
            continue;
        }

        out.push(line);
    }

    let stripped = out.join('\n');
    // Collapse 3+ trailing newlines that may have resulted from removal.
    stripped = stripped.replace(/\n{3,}$/g, '\n\n');
    return { content: stripped, removed };
}

function ensureTrailingBlankLine(content: string): string {
    if (content === '') {
        return '';
    }
    if (content.endsWith('\n\n')) {
        return content;
    }
    if (content.endsWith('\n')) {
        return content + '\n';
    }
    return content + '\n\n';
}

function buildZoteroSpec(pythonPath: string, config: vscode.WorkspaceConfiguration): CodexServerSpec {
    return {
        command: pythonPath,
        args: ['-m', 'zotero_mcp'],
        env: buildZoteroEnv(config),
    };
}

function buildPubmedSpec(pythonPath: string, config: vscode.WorkspaceConfiguration): CodexServerSpec {
    return {
        command: pythonPath,
        args: ['-m', PUBMED_SEARCH_ENTRYPOINT],
        env: buildPubmedEnv(config, getPrimaryWorkspaceFolder()),
    };
}

/**
 * Read the config. A missing file is an empty config; an existing but
 * unreadable file is an error, because treating it as empty would let the
 * caller overwrite the user's only copy.
 */
function readConfig(configPath: string): string {
    if (!fs.existsSync(configPath)) {
        return '';
    }
    return fs.readFileSync(configPath, 'utf-8');
}

/** The managed-block editor works on LF text; the file's own line endings are restored on write. */
function detectEol(content: string): '\r\n' | '\n' {
    return content.includes('\r\n') ? '\r\n' : '\n';
}

function toLf(content: string): string {
    return content.replace(/\r\n/g, '\n');
}

function withEol(content: string, eol: '\r\n' | '\n'): string {
    return eol === '\r\n' ? content.replace(/\n/g, '\r\n') : content;
}

function ensureFinalNewline(content: string): string {
    return content === '' || content.endsWith('\n') ? content : content + '\n';
}

/**
 * Install or update our managed MCP servers in Codex's config.toml.
 *
 * @returns true if the file was written/updated, false if no changes needed
 *          or Codex is not available.
 */
export function installCodexMcpServers(pythonPath: string): boolean {
    if (!isCodexAvailable()) {
        return false;
    }

    const configPath = getCodexConfigPath();
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const enableZotero = config.get<boolean>('enableZoteroKeeper', true);
    const enablePubmed = config.get<boolean>('enablePubmedSearch', true);

    const original = readConfig(configPath);
    const eol = detectEol(original);
    let content = toLf(original);

    // Always strip our managed blocks first — we re-render them from current
    // settings.  Stripping is idempotent if the block is absent.
    const zoteroStrip = stripManagedBlock(content, ZOTERO_SERVER_KEY);
    const pubmedStrip = stripManagedBlock(zoteroStrip.content, PUBMED_SERVER_KEY);
    content = pubmedStrip.content;

    // Append fresh blocks for each enabled server.
    const pieces: string[] = [];
    if (enableZotero) {
        pieces.push(renderManagedBlock(ZOTERO_SERVER_KEY, buildZoteroSpec(pythonPath, config)));
    }
    if (enablePubmed) {
        pieces.push(renderManagedBlock(PUBMED_SERVER_KEY, buildPubmedSpec(pythonPath, config)));
    }

    if (pieces.length > 0) {
        content = ensureTrailingBlankLine(content) + pieces.join('\n');
    } else if (zoteroStrip.removed || pubmedStrip.removed) {
        content = ensureFinalNewline(content.replace(/\n{3,}$/g, '\n'));
    } else {
        // All servers disabled and nothing of ours present: leave the file alone.
        return false;
    }

    const next = withEol(content, eol);
    if (next === original) {
        return false;
    }

    try {
        writeFileAtomic(configPath, next);
        console.log(`Codex MCP config updated: ${configPath}`);
        return true;
    } catch (error) {
        console.error('Failed to write Codex MCP config:', error);
        return false;
    }
}

/**
 * Remove our managed servers from Codex's config.toml (e.g. on disable).
 */
export function removeCodexMcpServers(): boolean {
    const configPath = getCodexConfigPath();
    if (!fs.existsSync(configPath)) {
        return false;
    }

    const original = readConfig(configPath);
    const eol = detectEol(original);
    const a = stripManagedBlock(toLf(original), ZOTERO_SERVER_KEY);
    const b = stripManagedBlock(a.content, PUBMED_SERVER_KEY);

    if (!a.removed && !b.removed) {
        return false;
    }

    try {
        writeFileAtomic(configPath, withEol(ensureFinalNewline(b.content), eol));
        console.log('Removed Zotero/PubMed from Codex MCP config');
        return true;
    } catch (error) {
        console.error('Failed to update Codex MCP config:', error);
        return false;
    }
}

// Re-export internals for unit testing.
export const __test__ = {
    stripManagedBlock,
    renderManagedBlock,
    buildZoteroSpec,
    buildPubmedSpec,
    escapeTomlString,
};
