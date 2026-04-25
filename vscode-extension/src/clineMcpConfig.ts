/**
 * Cline MCP Configuration Manager
 *
 * Automatically configures Zotero Keeper and PubMed Search MCP servers
 * in Cline's cline_mcp_settings.json so Cline users don't need to
 * manually set up STDIO servers.
 *
 * Cline settings file location (per Cline source: src/core/storage/disk.ts):
 *   <globalStorage>/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
 *
 * Cline does NOT use VS Code's native McpServerDefinitionProvider API;
 * it maintains its own McpHub that reads from the JSON file above.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { execSync } from 'child_process';
import { PUBMED_SEARCH_ENTRYPOINT, PUBMED_WORKSPACE_DIR_ENV } from './pubmedSearchPackage.js';

const CLINE_EXTENSION_ID = 'saoudrizwan.claude-dev';
const CLINE_SETTINGS_SUBDIR = 'settings';
const CLINE_MCP_SETTINGS_FILE = 'cline_mcp_settings.json';

// Keys we manage inside Cline's mcpServers object
const ZOTERO_SERVER_KEY = 'zotero-keeper';
const PUBMED_SERVER_KEY = 'pubmed-search-mcp';

interface ClineMcpServerEntry {
    command: string;
    args: string[];
    env?: Record<string, string>;
    alwaysAllow?: string[];
    disabled?: boolean;
    [key: string]: unknown;
}

interface ClineMcpSettings {
    mcpServers: Record<string, ClineMcpServerEntry>;
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
 * Derive the path to Cline's cline_mcp_settings.json from our own
 * extension globalStorageUri. VS Code places every extension's
 * global storage under  <user-data>/globalStorage/<ext-id>.
 */
function getClineMcpSettingsPath(context: vscode.ExtensionContext): string | undefined {
    const ourGlobalStorage = context.globalStorageUri.fsPath;
    // Walk up to the "globalStorage" folder, then into Cline's dir
    const globalStorageDir = path.dirname(ourGlobalStorage);
    const clineSettingsDir = path.join(globalStorageDir, CLINE_EXTENSION_ID, CLINE_SETTINGS_SUBDIR);
    return path.join(clineSettingsDir, CLINE_MCP_SETTINGS_FILE);
}

/**
 * Read existing Cline MCP settings, or return a blank scaffold.
 */
function readClineSettings(settingsPath: string): ClineMcpSettings {
    if (!fs.existsSync(settingsPath)) {
        return { mcpServers: {} };
    }
    try {
        const raw = fs.readFileSync(settingsPath, 'utf-8');
        const parsed = JSON.parse(raw) as ClineMcpSettings;
        if (!parsed.mcpServers || typeof parsed.mcpServers !== 'object') {
            return { mcpServers: {} };
        }
        return parsed;
    } catch {
        const backupPath = `${settingsPath}.invalid.${Date.now()}.bak`;
        try {
            fs.copyFileSync(settingsPath, backupPath);
            console.warn(`Backed up invalid Cline MCP settings to: ${backupPath}`);
        } catch (error) {
            console.warn('Failed to back up invalid Cline MCP settings:', error);
        }
        return { mcpServers: {} };
    }
}

/**
 * Write Cline MCP settings atomically (temp file + rename).
 */
function writeClineSettings(settingsPath: string, settings: ClineMcpSettings): void {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    const tmpPath = `${settingsPath}.tmp.${Date.now()}.json`;
    fs.writeFileSync(tmpPath, JSON.stringify(settings, null, 2), 'utf-8');
    fs.renameSync(tmpPath, settingsPath);
}

/**
 * Check whether a server entry is "ours" (managed by this extension).
 */
function isManagedByUs(entry: ClineMcpServerEntry | undefined): boolean {
    if (!entry) { return false; }
    // We always pass -m zotero_mcp or -m pubmed_search.presentation.mcp_server
    return entry.args?.some(a => a === 'zotero_mcp' || a === PUBMED_SEARCH_ENTRYPOINT) ?? false;
}

/**
 * Build the Zotero Keeper MCP server entry for Cline.
 */
function buildZoteroEntry(pythonPath: string, config: vscode.WorkspaceConfiguration): ClineMcpServerEntry {
    const host = config.get<string>('zoteroHost', 'localhost');
    const port = config.get<number>('zoteroPort', 23119);
    return {
        command: pythonPath,
        args: ['-m', 'zotero_mcp'],
        env: {
            ZOTERO_HOST: host,
            ZOTERO_PORT: String(port),
        },
        disabled: false,
    };
}

/**
 * Build the PubMed Search MCP server entry for Cline.
 */
function buildPubmedEntry(pythonPath: string, config: vscode.WorkspaceConfiguration): ClineMcpServerEntry {
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
        disabled: false,
    };
}

function mergeManagedEntry(
    existing: ClineMcpServerEntry | undefined,
    next: ClineMcpServerEntry
): ClineMcpServerEntry {
    if (!existing || !isManagedByUs(existing)) {
        return next;
    }

    return {
        ...existing,
        ...next,
        // Preserve Cline-local user choices and Cline-specific metadata.
        disabled: existing.disabled ?? next.disabled,
        alwaysAllow: existing.alwaysAllow,
    };
}

/**
 * Install or update our managed MCP servers in Cline's settings.
 *
 * @returns true if settings were written/updated, false if Cline not installed or no changes needed
 */
export function installClineMcpServers(
    context: vscode.ExtensionContext,
    pythonPath: string
): boolean {
    if (!isClineInstalled(context)) {
        return false;
    }

    const settingsPath = getClineMcpSettingsPath(context);
    if (!settingsPath) {
        console.warn('Could not determine Cline MCP settings path');
        return false;
    }

    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const enableZotero = config.get<boolean>('enableZoteroKeeper', true);
    const enablePubmed = config.get<boolean>('enablePubmedSearch', true);

    const settings = readClineSettings(settingsPath);
    let changed = false;

    // Zotero Keeper
    if (enableZotero) {
        const existing = settings.mcpServers[ZOTERO_SERVER_KEY];
        const newEntry = mergeManagedEntry(existing, buildZoteroEntry(pythonPath, config));
        if (!existing || (isManagedByUs(existing) && !entriesEqual(existing, newEntry))) {
            settings.mcpServers[ZOTERO_SERVER_KEY] = newEntry;
            changed = true;
        }
    } else if (settings.mcpServers[ZOTERO_SERVER_KEY] && isManagedByUs(settings.mcpServers[ZOTERO_SERVER_KEY])) {
        delete settings.mcpServers[ZOTERO_SERVER_KEY];
        changed = true;
    }

    // PubMed Search
    if (enablePubmed) {
        const existing = settings.mcpServers[PUBMED_SERVER_KEY];
        const newEntry = mergeManagedEntry(existing, buildPubmedEntry(pythonPath, config));
        if (!existing || (isManagedByUs(existing) && !entriesEqual(existing, newEntry))) {
            settings.mcpServers[PUBMED_SERVER_KEY] = newEntry;
            changed = true;
        }
    } else if (settings.mcpServers[PUBMED_SERVER_KEY] && isManagedByUs(settings.mcpServers[PUBMED_SERVER_KEY])) {
        delete settings.mcpServers[PUBMED_SERVER_KEY];
        changed = true;
    }

    if (changed) {
        try {
            writeClineSettings(settingsPath, settings);
            console.log(`Cline MCP settings updated: ${settingsPath}`);
            return true;
        } catch (error) {
            console.error('Failed to write Cline MCP settings:', error);
            return false;
        }
    }

    return false;
}

/**
 * Remove our managed servers from Cline settings (e.g. on uninstall/disable).
 */
export function removeClineMcpServers(context: vscode.ExtensionContext): boolean {
    const settingsPath = getClineMcpSettingsPath(context);
    if (!settingsPath || !fs.existsSync(settingsPath)) {
        return false;
    }

    const settings = readClineSettings(settingsPath);
    let changed = false;

    if (settings.mcpServers[ZOTERO_SERVER_KEY] && isManagedByUs(settings.mcpServers[ZOTERO_SERVER_KEY])) {
        delete settings.mcpServers[ZOTERO_SERVER_KEY];
        changed = true;
    }
    if (settings.mcpServers[PUBMED_SERVER_KEY] && isManagedByUs(settings.mcpServers[PUBMED_SERVER_KEY])) {
        delete settings.mcpServers[PUBMED_SERVER_KEY];
        changed = true;
    }

    if (changed) {
        try {
            writeClineSettings(settingsPath, settings);
            console.log('Removed Zotero/PubMed from Cline MCP settings');
            return true;
        } catch (error) {
            console.error('Failed to update Cline MCP settings:', error);
            return false;
        }
    }

    return false;
}

/**
 * Check whether Cline appears to be installed (extension global storage dir exists).
 */
export function isClineInstalled(context: vscode.ExtensionContext): boolean {
    if (vscode.extensions.getExtension(CLINE_EXTENSION_ID)) {
        return true;
    }

    const ourGlobalStorage = context.globalStorageUri.fsPath;
    const globalStorageDir = path.dirname(ourGlobalStorage);
    const clineExtensionDir = path.join(globalStorageDir, CLINE_EXTENSION_ID);
    return fs.existsSync(clineExtensionDir);
}

/**
 * Shallow comparison of two server entries (command, args, env keys).
 */
function entriesEqual(a: ClineMcpServerEntry, b: ClineMcpServerEntry): boolean {
    if (a.command !== b.command) { return false; }
    if (JSON.stringify(a.args) !== JSON.stringify(b.args)) { return false; }
    if ((a.disabled ?? false) !== (b.disabled ?? false)) { return false; }

    const aEnv = a.env ?? {};
    const bEnv = b.env ?? {};
    const aKeys = Object.keys(aEnv).sort();
    const bKeys = Object.keys(bEnv).sort();
    if (aKeys.length !== bKeys.length) { return false; }
    for (let i = 0; i < aKeys.length; i++) {
        if (aKeys[i] !== bKeys[i] || aEnv[aKeys[i]] !== bEnv[bKeys[i]]) {
            return false;
        }
    }

    return true;
}
