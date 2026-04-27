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
import { execSync } from 'child_process';
import { PUBMED_SEARCH_ENTRYPOINT, PUBMED_WORKSPACE_DIR_ENV } from './pubmedSearchPackage.js';

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

function getGitEmail(): string {
    try {
        return execSync('git config user.email', {
            encoding: 'utf-8',
            stdio: 'pipe',
            timeout: 5000,
        }).trim();
    } catch {
        return '';
    }
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
    // TOML basic strings: backslash + double-quote require escaping; control
    // chars use \uXXXX. We additionally escape backslashes for Windows paths
    // so `C:\Users\...` round-trips correctly.
    return value
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
        .replace(/\t/g, '\\t');
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
    const host = config.get<string>('zoteroHost', 'localhost');
    const port = config.get<number>('zoteroPort', 23119);
    return {
        command: pythonPath,
        args: ['-m', 'zotero_mcp'],
        env: {
            ZOTERO_HOST: host,
            ZOTERO_PORT: String(port),
        },
    };
}

function buildPubmedSpec(pythonPath: string, config: vscode.WorkspaceConfiguration): CodexServerSpec {
    const env: Record<string, string> = {};

    const ncbiEmail = config.get<string>('ncbiEmail', '') || getGitEmail();
    const ncbiApiKey = config.get<string>('ncbiApiKey', '');
    const coreApiKey = config.get<string>('coreApiKey', '');
    const openAlexApiKey = config.get<string>('openAlexApiKey', '');
    const semanticScholarApiKey = config.get<string>('semanticScholarApiKey', '');
    const httpProxy = config.get<string>('httpProxy', '');
    const httpsProxy = config.get<string>('httpsProxy', '');
    const openUrlResolver = config.get<string>('openUrlResolver', '');
    const openUrlPreset = config.get<string>('openUrlPreset', '');

    if (ncbiEmail) { env['NCBI_EMAIL'] = ncbiEmail; }
    if (ncbiApiKey) { env['NCBI_API_KEY'] = ncbiApiKey; }
    if (coreApiKey) { env['CORE_API_KEY'] = coreApiKey; }
    if (openAlexApiKey) { env['OPENALEX_API_KEY'] = openAlexApiKey; }
    if (semanticScholarApiKey) { env['S2_API_KEY'] = semanticScholarApiKey; }
    if (httpProxy) { env['HTTP_PROXY'] = httpProxy; }
    if (httpsProxy) { env['HTTPS_PROXY'] = httpsProxy; }
    if (openUrlPreset) { env['OPENURL_PRESET'] = openUrlPreset; }
    if (openUrlResolver) { env['OPENURL_RESOLVER'] = openUrlResolver; }

    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (workspaceFolder) {
        env[PUBMED_WORKSPACE_DIR_ENV] = workspaceFolder;
    }

    return {
        command: pythonPath,
        args: ['-m', PUBMED_SEARCH_ENTRYPOINT],
        env,
    };
}

function readConfig(configPath: string): string {
    if (!fs.existsSync(configPath)) {
        return '';
    }
    try {
        return fs.readFileSync(configPath, 'utf-8');
    } catch (error) {
        console.warn(`Failed to read Codex config at ${configPath}:`, error);
        // Back up unreadable file before overwriting
        try {
            fs.copyFileSync(configPath, `${configPath}.unreadable.${Date.now()}.bak`);
        } catch {
            // ignore
        }
        return '';
    }
}

function writeConfigAtomic(configPath: string, content: string): void {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    const tmp = `${configPath}.tmp.${Date.now()}`;
    fs.writeFileSync(tmp, content, 'utf-8');
    fs.renameSync(tmp, configPath);
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

    let content = readConfig(configPath);
    const original = content;

    // Always strip our managed blocks first — we re-render them from current
    // settings.  Stripping is idempotent if the block is absent.
    const zoteroStrip = stripManagedBlock(content, ZOTERO_SERVER_KEY);
    content = zoteroStrip.content;
    const pubmedStrip = stripManagedBlock(content, PUBMED_SERVER_KEY);
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
        content = ensureTrailingBlankLine(content);
        content = content + pieces.join('\n');
    } else {
        // All servers disabled — only write if we removed something.
        content = content.replace(/\n{3,}$/g, '\n');
    }

    if (content === original) {
        return false;
    }

    try {
        writeConfigAtomic(configPath, content);
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
    const a = stripManagedBlock(original, ZOTERO_SERVER_KEY);
    const b = stripManagedBlock(a.content, PUBMED_SERVER_KEY);

    if (!a.removed && !b.removed) {
        return false;
    }

    try {
        writeConfigAtomic(configPath, b.content);
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
