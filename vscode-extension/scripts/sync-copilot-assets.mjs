import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, '..');
const repoRoot = path.resolve(extensionRoot, '..');
const assetRoot = path.join(extensionRoot, 'resources', 'repo-assets');

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
 * - .sh files: force LF (CRLF breaks shebang on Linux/macOS)
 * - .ps1 files: force CRLF (PowerShell convention on Windows)
 * - .json files: force LF (RFC 8259, no BOM)
 * - .md files: keep as-is (CRLF is harmless)
 * - All files: strip UTF-8 BOM if present
 */
function normalizeLineEndings(targetPath) {
    const ext = path.extname(targetPath).toLowerCase();
    const raw = fs.readFileSync(targetPath);

    // Strip UTF-8 BOM if present
    let content = raw[0] === 0xEF && raw[1] === 0xBB && raw[2] === 0xBF
        ? raw.subarray(3)
        : raw;

    if (ext === '.sh' || ext === '.json') {
        // Force LF for shell scripts and JSON
        const text = content.toString('utf8').replace(/\r\n/g, '\n');
        fs.writeFileSync(targetPath, text, 'utf8');
    } else if (ext === '.ps1') {
        // Force CRLF for PowerShell scripts (Windows convention)
        const text = content.toString('utf8').replace(/\r\n/g, '\n').replace(/\n/g, '\r\n');
        fs.writeFileSync(targetPath, text, 'utf8');
    }
    // .md and other files: keep as-is (CRLF is harmless for markdown)
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
