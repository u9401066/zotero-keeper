import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(scriptDir, '..');
const assetRoot = path.join(extensionRoot, 'resources', 'repo-assets');
const syncScript = path.join(scriptDir, 'sync-copilot-assets.mjs');

function snapshotDirectory(root) {
    const snapshot = new Map();

    function normalizedContent(filePath) {
        const raw = fs.readFileSync(filePath);
        let content = raw[0] === 0xEF && raw[1] === 0xBB && raw[2] === 0xBF
            ? raw.subarray(3)
            : raw;

        if (['.md', '.json', '.sh', '.ps1'].includes(path.extname(filePath).toLowerCase())) {
            content = Buffer.from(content.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
        }

        return content;
    }

    function walk(dir) {
        if (!fs.existsSync(dir)) {
            return;
        }

        const entries = fs.readdirSync(dir, { withFileTypes: true })
            .sort((a, b) => a.name.localeCompare(b.name));

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                walk(fullPath);
                continue;
            }
            if (!entry.isFile()) {
                continue;
            }

            const relativePath = path.relative(root, fullPath).replaceAll(path.sep, '/');
            const digest = createHash('sha256').update(normalizedContent(fullPath)).digest('hex');
            snapshot.set(relativePath, digest);
        }
    }

    walk(root);
    return snapshot;
}

function diffSnapshots(before, after) {
    const changes = [];
    const paths = new Set([...before.keys(), ...after.keys()]);

    for (const relativePath of [...paths].sort()) {
        if (!before.has(relativePath)) {
            changes.push(`added ${relativePath}`);
        } else if (!after.has(relativePath)) {
            changes.push(`removed ${relativePath}`);
        } else if (before.get(relativePath) !== after.get(relativePath)) {
            changes.push(`changed ${relativePath}`);
        }
    }

    return changes;
}

const before = snapshotDirectory(assetRoot);
execFileSync(process.execPath, [syncScript], {
    cwd: extensionRoot,
    stdio: 'inherit',
});
const after = snapshotDirectory(assetRoot);
const changes = diffSnapshots(before, after);

if (changes.length > 0) {
    console.error('Assistant assets are not synchronized with their source files.');
    for (const change of changes.slice(0, 50)) {
        console.error(`- ${change}`);
    }
    if (changes.length > 50) {
        console.error(`...and ${changes.length - 50} more`);
    }
    process.exit(1);
}

console.log('Assistant assets are synchronized.');
