import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { installHarnessAssets, HARNESS_MANIFEST } from '../harnessAssets';

describe('Harness preservation', () => {
    let root: string;
    let bundle: string;
    let workspace: string;
    const write = (base: string, relative: string, content: string) => {
        const file = path.join(base, relative);
        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.writeFileSync(file, content);
        return file;
    };
    beforeEach(() => {
        root = fs.mkdtempSync(path.join(os.tmpdir(), 'keeper-harness-'));
        bundle = path.join(root, 'bundle');
        workspace = path.join(root, 'workspace');
        fs.mkdirSync(workspace);
        fs.mkdirSync(path.join(bundle, 'pubmed-search-mcp'), { recursive: true });
        write(bundle, 'keeper/AGENTS.md', '# Zotero + PubMed MCP Codex Harness\noriginal');
        write(bundle, 'keeper/.codex/skills/zotero-keeper-harness/SKILL.md', 'original skill');
    });
    afterEach(() => fs.rmSync(root, { recursive: true, force: true }));

    it('installs once and does not rewrite unchanged files or the ledger', () => {
        const first = installHarnessAssets(bundle, workspace, '0.9.0');
        assert.strictEqual(first.installed.length, 2);
        const files = ['AGENTS.md', HARNESS_MANIFEST];
        for (const f of files) { fs.utimesSync(path.join(workspace, f), 1000, 1000); }
        const second = installHarnessAssets(bundle, workspace, '0.9.0');
        assert.strictEqual(second.unchanged.length, 2);
        for (const f of files) { assert.strictEqual(fs.statSync(path.join(workspace, f)).mtimeMs, 1000000); }
    });
    it('preserves edited official headings, rules, hooks and skills', () => {
        const names = ['AGENTS.md', '.clinerules/70-pubmed-mcp-tools.md', '.github/hooks/pipeline.json', '.codex/skills/zotero-keeper-harness/SKILL.md'];
        for (const name of names) { write(bundle, 'keeper/' + name, 'official'); }
        installHarnessAssets(bundle, workspace, '0.9.0');
        for (const name of names) {
            write(workspace, name, '# Zotero + PubMed MCP Codex Harness\nmy edit');
            write(bundle, 'keeper/' + name, 'upgrade');
        }
        const result = installHarnessAssets(bundle, workspace, '0.10.0');
        assert.strictEqual(result.updated.length, 0);
        assert.strictEqual(result.preserved.length, 4);
        for (const name of names) { assert.match(fs.readFileSync(path.join(workspace, name), 'utf8'), /my edit/); }
    });
    it('upgrades only hash-matched assets and retains a recovery backup', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        const original = fs.readFileSync(path.join(workspace, 'AGENTS.md'), 'utf8');
        write(bundle, 'keeper/AGENTS.md', 'new');
        const result = installHarnessAssets(bundle, workspace, '0.10.0');
        assert.deepStrictEqual(result.updated, ['AGENTS.md']);
        const backupRoot = path.join(workspace, '.vscode/zotero-mcp-backups/0.9.0');
        const hash = fs.readdirSync(backupRoot)[0];
        assert.strictEqual(fs.readFileSync(path.join(backupRoot, hash, 'AGENTS.md'), 'utf8'), original);
    });
    it('refuses a downgrade, including adding files from the old bundle', () => {
        installHarnessAssets(bundle, workspace, '0.10.0');
        write(bundle, 'keeper/AGENTS.md', 'old');
        write(bundle, 'keeper/old.md', 'obsolete');
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped!, /Newer/);
        assert.ok(!fs.existsSync(path.join(workspace, 'old.md')));
    });
    it('preserves unknown files, including empty files, without claiming ownership', () => {
        write(workspace, 'AGENTS.md', '');
        const result = installHarnessAssets(bundle, workspace, '0.9.0');
        assert.deepStrictEqual(result.preserved, ['AGENTS.md']);
        assert.strictEqual(fs.readFileSync(path.join(workspace, 'AGENTS.md'), 'utf8'), '');
        const manifest = JSON.parse(fs.readFileSync(path.join(workspace, HARNESS_MANIFEST), 'utf8'));
        assert.ok(!Object.hasOwn(manifest.files, 'AGENTS.md'));
    });
    it('does not resurrect deleted files or delete custom prefixed skills/backups', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        fs.unlinkSync(path.join(workspace, 'AGENTS.md'));
        write(workspace, '.claude/skills/pubmed-my-research/SKILL.md', 'user');
        write(workspace, '.github/copilot-instructions.md.old', 'backup');
        installHarnessAssets(bundle, workspace, '0.10.0');
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
        assert.ok(fs.existsSync(path.join(workspace, '.claude/skills/pubmed-my-research/SKILL.md')));
        assert.ok(fs.existsSync(path.join(workspace, '.github/copilot-instructions.md.old')));
    });
    it('fails closed on corrupt manifests', () => {
        write(workspace, HARNESS_MANIFEST, '{');
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.9.0'));
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
    });
    it('preserves the entire custom skill instead of injecting sibling scripts', () => {
        const skill = '.codex/skills/zotero-keeper-harness';
        write(workspace, skill + '/SKILL.md', 'my skill');
        write(bundle, 'keeper/' + skill + '/scripts/run.py', 'new script');
        installHarnessAssets(bundle, workspace, '0.9.0');
        assert.ok(!fs.existsSync(path.join(workspace, skill, 'scripts/run.py')));
    });
    it('preserves all files of a managed skill if one file is edited or added', () => {
        const skill = '.codex/skills/zotero-keeper-harness';
        installHarnessAssets(bundle, workspace, '0.9.0');
        write(workspace, skill + '/custom.md', 'my reference');
        write(bundle, 'keeper/' + skill + '/SKILL.md', 'upgrade');
        installHarnessAssets(bundle, workspace, '0.10.0');
        assert.strictEqual(fs.readFileSync(path.join(workspace, skill, 'SKILL.md'), 'utf8'), 'original skill');
    });
    it('does not install while another window holds the installation lock', () => {
        write(workspace, '.vscode/zotero-mcp-assets.lock', 'other window');
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped!, /locked/);
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
    });
    it('does not write through symlinked harness directories', function () {
        if (process.platform === 'win32') { this.skip(); }
        const outside = path.join(root, 'outside');
        fs.mkdirSync(outside);
        fs.symlinkSync(outside, path.join(workspace, '.codex'));
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.9.0'), /symbolic link/);
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
        assert.deepStrictEqual(fs.readdirSync(outside), []);
    });
    it('skips maintainer source workspaces', () => {
        write(workspace, 'vscode-extension/scripts/sync-copilot-assets.mjs', 'source');
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped!, /Source repository/);
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
    });
    it('does not replace a differing bundle from the same extension version', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        write(bundle, 'keeper/AGENTS.md', 'different development build');
        assert.deepStrictEqual(installHarnessAssets(bundle, workspace, '0.9.0').preserved, ['AGENTS.md']);
    });
});
