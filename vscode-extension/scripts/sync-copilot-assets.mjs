import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(extensionRoot, '..');
const assetRoot = path.join(extensionRoot, 'resources', 'repo-assets');

// Curated user-facing PubMed skills bundled into the VSIX. The upstream
// repository contains additional maintainer/internal skills; these are
// intentionally excluded from end-user installation.
const pubmedUserSkillNames = [
    'pubmed-quick-search',
    'pubmed-systematic-search',
    'pubmed-pico-search',
    'pubmed-multi-source-search',
    'pubmed-paper-exploration',
    'pubmed-fulltext-access',
    'pubmed-export-citations',
    'pubmed-gene-drug-research',
    'pubmed-mcp-tools-reference',
    'pipeline-persistence',
];

const keeperClineRuleFiles = [
    '00-zotero-project.md',
    '10-zotero-python.md',
    '20-zotero-vscode-extension.md',
    '30-zotero-research-workflow.md',
    '40-zotero-release.md',
    'workflows/zotero-full-check.md',
    'workflows/zotero-mcp-setup.md',
    'workflows/zotero-release-publish.md',
    'workflows/zotero-skills-audit.md',
];

const pubmedClineRuleFiles = [
    '50-pubmed-project.md',
    '60-pubmed-python.md',
    '70-pubmed-mcp-tools.md',
    '80-pubmed-release.md',
    'workflows/pubmed-full-check.md',
    'workflows/pubmed-mcp-setup.md',
    'workflows/pubmed-release-publish.md',
    'workflows/pubmed-skills-audit.md',
];

const mappings = [
    {
        source: path.join(repoRoot, '.github', 'copilot-user-instructions.md'),
        target: path.join(assetRoot, 'keeper', '.github', 'copilot-instructions.md'),
    },
    {
        source: path.join(repoRoot, '.github', 'zotero-research-workflow.md'),
        target: path.join(assetRoot, 'keeper', '.github', 'zotero-research-workflow.md'),
    },
    {
        source: path.join(repoRoot, 'AGENTS.md'),
        target: path.join(assetRoot, 'keeper', 'AGENTS.md'),
    },
    {
        source: path.join(repoRoot, '.codex', 'skills', 'zotero-keeper-harness'),
        target: path.join(assetRoot, 'keeper', '.codex', 'skills', 'zotero-keeper-harness'),
    },
    {
        source: path.join(repoRoot, '.cline', 'skills', 'zotero-keeper-harness'),
        target: path.join(assetRoot, 'keeper', '.cline', 'skills', 'zotero-keeper-harness'),
    },
    ...keeperClineRuleFiles.map((ruleFile) => ({
        source: path.join(repoRoot, '.clinerules', ruleFile),
        target: path.join(assetRoot, 'keeper', '.clinerules', ruleFile),
    })),
    {
        source: path.join(repoRoot, 'external', 'pubmed-search-mcp', '.github', 'agents', 'research.agent.md'),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.github', 'agents', 'research.agent.md'),
    },
    {
        source: path.join(repoRoot, 'external', 'pubmed-search-mcp', '.github', 'hooks', 'pipeline-enforcer.json'),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.github', 'hooks', 'pipeline-enforcer.json'),
    },
    {
        source: path.join(repoRoot, 'external', 'pubmed-search-mcp', '.github', 'hooks', 'copilot-tool-policy.json'),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.github', 'hooks', 'copilot-tool-policy.json'),
    },
    {
        source: path.join(repoRoot, 'external', 'pubmed-search-mcp', 'scripts', 'hooks', 'copilot'),
        target: path.join(assetRoot, 'pubmed-search-mcp', 'scripts', 'hooks', 'copilot'),
    },
    {
        source: path.join(repoRoot, '.cline', 'skills', 'pubmed-search-mcp-harness'),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.cline', 'skills', 'pubmed-search-mcp-harness'),
    },
    {
        source: path.join(repoRoot, '.codex', 'skills', 'pubmed-search-mcp-harness'),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.codex', 'skills', 'pubmed-search-mcp-harness'),
    },
    ...pubmedClineRuleFiles.map((ruleFile) => ({
        source: path.join(repoRoot, '.clinerules', ruleFile),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.clinerules', ruleFile),
    })),
    ...pubmedUserSkillNames.map((skillName) => ({
        source: path.join(repoRoot, 'external', 'pubmed-search-mcp', '.claude', 'skills', skillName),
        target: path.join(assetRoot, 'pubmed-search-mcp', '.claude', 'skills', skillName),
    })),
];

function ensureParentDirectory(targetPath) {
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}

/**
 * Normalize line endings for cross-platform compatibility.
 * - Text assets: force LF so pre-commit and Linux CI agree with Windows sync
 * - All files: strip UTF-8 BOM if present
 */
function normalizeLineEndings(targetPath) {
    const ext = path.extname(targetPath).toLowerCase();
    const raw = fs.readFileSync(targetPath);

    // Strip UTF-8 BOM if present
    let content = raw[0] === 0xEF && raw[1] === 0xBB && raw[2] === 0xBF
        ? raw.subarray(3)
        : raw;

    if (['.md', '.json', '.sh', '.ps1'].includes(ext)) {
        const text = content.toString('utf8').replace(/\r\n/g, '\n');
        fs.writeFileSync(targetPath, text, 'utf8');
    }
}

function copyRecursive(sourcePath, targetPath) {
    const stat = fs.statSync(sourcePath);
    if (stat.isDirectory()) {
        fs.mkdirSync(targetPath, { recursive: true });
        for (const entry of fs.readdirSync(sourcePath, { withFileTypes: true })) {
            copyRecursive(path.join(sourcePath, entry.name), path.join(targetPath, entry.name));
        }
        return;
    }

    ensureParentDirectory(targetPath);
    fs.copyFileSync(sourcePath, targetPath);
    normalizeLineEndings(targetPath);
}

function main() {
    fs.rmSync(assetRoot, { recursive: true, force: true });

    for (const mapping of mappings) {
        if (!fs.existsSync(mapping.source)) {
            throw new Error(`Missing asset source: ${mapping.source}`);
        }
        copyRecursive(mapping.source, mapping.target);
        console.log(`Synced ${path.relative(repoRoot, mapping.source)} -> ${path.relative(extensionRoot, mapping.target)}`);
    }
}

main();
