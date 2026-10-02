/**
 * Shared MCP server configuration helpers.
 *
 * The VS Code provider, the Cline settings writer and the Codex TOML writer
 * must hand the same environment to the same servers; keeping the mapping in
 * one place prevents the three consumers from drifting apart.
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { execFileSync } from 'child_process';
import { randomUUID } from 'crypto';
import { PUBMED_WORKSPACE_DIR_ENV } from './pubmedSearchPackage.js';

type ConfigReader = Pick<vscode.WorkspaceConfiguration, 'get'>;

const GIT_EMAIL_TTL_MS = 60_000;
const gitEmailCache = new Map<string, { value: string; at: number }>();

/** Test hook: forget cached `git config user.email` lookups. */
export function resetGitEmailCache(): void {
    gitEmailCache.clear();
}

/**
 * `git config user.email` fallback for the NCBI contact address. The lookup is
 * synchronous, so results (including failures) are cached briefly: every
 * provider refresh would otherwise block the extension host on a process spawn.
 */
export function getGitEmail(cwd?: string): string {
    const key = cwd ?? '';
    const cached = gitEmailCache.get(key);
    if (cached && Date.now() - cached.at < GIT_EMAIL_TTL_MS) {
        return cached.value;
    }

    let value = '';
    try {
        value = execFileSync('git', ['config', 'user.email'], {
            encoding: 'utf-8',
            stdio: 'pipe',
            timeout: 5000,
            windowsHide: true,
            ...(cwd && fs.existsSync(cwd) ? { cwd } : {}),
        }).trim();
    } catch {
        value = '';
    }
    gitEmailCache.set(key, { value, at: Date.now() });
    return value;
}

export function getPrimaryWorkspaceFolder(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

export function buildZoteroEnv(config: ConfigReader): Record<string, string> {
    return {
        ZOTERO_HOST: config.get<string>('zoteroHost', 'localhost'),
        ZOTERO_PORT: String(config.get<number>('zoteroPort', 23119)),
    };
}

/** Optional settings are only exported when non-empty so servers keep their own defaults. */
export function buildPubmedEnv(config: ConfigReader, workspaceFolder?: string): Record<string, string> {
    const env: Record<string, string> = {};
    const optional: Array<[string, string]> = [
        ['NCBI_API_KEY', 'ncbiApiKey'],
        ['CORE_API_KEY', 'coreApiKey'],
        ['OPENALEX_API_KEY', 'openAlexApiKey'],
        ['S2_API_KEY', 'semanticScholarApiKey'],
        ['HTTP_PROXY', 'httpProxy'],
        ['HTTPS_PROXY', 'httpsProxy'],
        ['OPENURL_PRESET', 'openUrlPreset'],
        ['OPENURL_RESOLVER', 'openUrlResolver'],
    ];

    const email = config.get<string>('ncbiEmail', '').trim() || getGitEmail(workspaceFolder);
    if (email) { env['NCBI_EMAIL'] = email; }
    for (const [envName, settingKey] of optional) {
        const value = config.get<string>(settingKey, '').trim();
        if (value) { env[envName] = value; }
    }
    if (workspaceFolder) { env[PUBMED_WORKSPACE_DIR_ENV] = workspaceFolder; }
    return env;
}

/**
 * Replace `target` atomically (temp file in the same directory + rename).
 * An existing file keeps its permission bits (and a read-only file is refused);
 * a new file is created owner-only because these files carry API keys. The
 * temp file never outlives a failure.
 */
export function writeFileAtomic(target: string, content: string): void {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    let mode = 0o600;
    if (fs.existsSync(target)) {
        // Replacing by rename would silently bypass a read-only marker.
        fs.accessSync(target, fs.constants.W_OK);
        mode = fs.statSync(target).mode & 0o777;
    }

    const temporary = `${target}.${randomUUID()}.tmp`;
    try {
        const handle = fs.openSync(temporary, 'wx', mode);
        try {
            // open(2) applies the umask; the intended mode must be exact.
            fs.fchmodSync(handle, mode);
            fs.writeFileSync(handle, content, 'utf-8');
            fs.fsyncSync(handle);
        } finally {
            fs.closeSync(handle);
        }
        fs.renameSync(temporary, target);
    } finally {
        fs.rmSync(temporary, { force: true });
    }
}

/** Remove `user:password@` from a URL before it is shown in the UI. */
export function redactCredentials(value: string): string {
    return value.replace(/(\/\/)[^/@\s]*@/, '$1***@');
}
