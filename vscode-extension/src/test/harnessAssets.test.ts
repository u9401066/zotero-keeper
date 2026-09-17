import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import fileSystem from 'fs';
import * as sinon from 'sinon';
import { installHarnessAssets, HARNESS_MANIFEST, HARNESS_PENDING } from '../harnessAssets';

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
    afterEach(() => { sinon.restore(); fs.rmSync(root, { recursive: true, force: true }); });

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
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped ?? '', /Newer/);
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
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped ?? '', /locked/);
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
        assert.match(installHarnessAssets(bundle, workspace, '0.9.0').skipped ?? '', /Source repository/);
        assert.ok(!fs.existsSync(path.join(workspace, 'AGENTS.md')));
    });
    it('does not replace a differing bundle from the same extension version', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        write(bundle, 'keeper/AGENTS.md', 'different development build');
        assert.deepStrictEqual(installHarnessAssets(bundle, workspace, '0.9.0').preserved, ['AGENTS.md']);
    });
    it('rolls back the whole skill, new files and ledger if committing the ledger fails', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        const ledger = fs.readFileSync(path.join(workspace, HARNESS_MANIFEST));
        const original = fs.readFileSync(path.join(workspace, 'AGENTS.md'));
        write(bundle, 'keeper/AGENTS.md', 'upgrade');
        write(bundle, 'keeper/.codex/skills/zotero-keeper-harness/SKILL.md', 'upgrade skill');
        write(bundle, 'keeper/.codex/skills/zotero-keeper-harness/new.md', 'new sibling');
        const rename = fileSystem.renameSync;
        sinon.stub(fileSystem, 'renameSync').callsFake((source, target) => {
            if (String(target) === path.join(workspace, HARNESS_MANIFEST)) { throw new Error('disk failure'); }
            rename(source, target);
        });
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.10.0'), /Previous assets and ledger restored/);
        assert.deepStrictEqual(fs.readFileSync(path.join(workspace, 'AGENTS.md')), original);
        assert.deepStrictEqual(fs.readFileSync(path.join(workspace, HARNESS_MANIFEST)), ledger);
        assert.strictEqual(fs.readFileSync(path.join(workspace, '.codex/skills/zotero-keeper-harness/SKILL.md'), 'utf8'), 'original skill');
        assert.ok(!fs.existsSync(path.join(workspace, '.codex/skills/zotero-keeper-harness/new.md')));
        assert.ok(!fs.existsSync(path.join(workspace, HARNESS_PENDING)));
        sinon.restore();
        assert.strictEqual(installHarnessAssets(bundle, workspace, '0.10.0').updated.length, 2);
    });
    it('preserves edits during rollback and blocks further updates pending review', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        write(bundle, 'keeper/AGENTS.md', 'upgrade');
        const rename = fileSystem.renameSync;
        sinon.stub(fileSystem, 'renameSync').callsFake((source, target) => {
            if (String(target) === path.join(workspace, HARNESS_MANIFEST)) {
                write(workspace, 'AGENTS.md', 'concurrent user edit');
                throw new Error('disk failure');
            }
            rename(source, target);
        });
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.10.0'), /further updates are blocked/);
        assert.strictEqual(fs.readFileSync(path.join(workspace, 'AGENTS.md'), 'utf8'), 'concurrent user edit');
        const pending = JSON.parse(fs.readFileSync(path.join(workspace, HARNESS_PENDING), 'utf8'));
        assert.strictEqual(pending.to, '0.10.0');
        assert.ok(pending.files.find((f: { path: string }) => f.path === 'AGENTS.md').backup);
        sinon.restore();
        assert.match(installHarnessAssets(bundle, workspace, '0.10.0').skipped ?? '', /Interrupted harness update/);
    });
    it('refuses a modified recovery backup before upgrading any asset', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        const ledger = fs.readFileSync(path.join(workspace, HARNESS_MANIFEST));
        const manifest = JSON.parse(ledger.toString());
        write(workspace, `.vscode/zotero-mcp-backups/0.9.0/${manifest.files['AGENTS.md']}/AGENTS.md`, 'user-modified backup');
        write(bundle, 'keeper/AGENTS.md', 'upgrade');
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.10.0'), /backup was modified/);
        assert.deepStrictEqual(fs.readFileSync(path.join(workspace, HARNESS_MANIFEST)), ledger);
        assert.match(fs.readFileSync(path.join(workspace, 'AGENTS.md'), 'utf8'), /original/);
    });
    it('rejects unsafe ledger paths and invalid semantic versions before asset writes', () => {
        installHarnessAssets(bundle, workspace, '0.9.0');
        const ledger = JSON.parse(fs.readFileSync(path.join(workspace, HARNESS_MANIFEST), 'utf8'));
        ledger.files['../outside'] = ledger.files['AGENTS.md'];
        write(workspace, HARNESS_MANIFEST, JSON.stringify(ledger));
        assert.throws(() => installHarnessAssets(bundle, workspace, '0.10.0'), /Invalid harness path/);
        for (const version of ['00.9.0', '0.9.0-beta', '9007199254740992.0.0']) {
            assert.throws(() => installHarnessAssets(bundle, workspace, version), /semantic version/);
        }
    });
});
