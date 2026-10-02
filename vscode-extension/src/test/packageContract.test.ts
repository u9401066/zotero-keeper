import { describe, it } from 'mocha';
import * as assert from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import { ZOTERO_KEEPER_SOURCE_URL } from '../zoteroKeeperPackage.js';

/**
 * Contract between package.json and the code: drift here ships a broken VSIX
 * (a setting the code reads but VS Code does not know, a default that differs
 * from what the UI shows, an engine older than the API we compile against).
 */
const extensionRoot = path.resolve(__dirname, '..', '..');
const manifest = JSON.parse(fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf-8'));
const properties: Record<string, { default?: unknown }> = manifest.contributes.configuration.properties;

function sourceFiles(): Array<{ name: string; text: string }> {
    const srcDir = path.join(extensionRoot, 'src');
    return fs.readdirSync(srcDir)
        .filter(name => name.endsWith('.ts') && !name.endsWith('.d.ts'))
        .map(name => ({ name, text: fs.readFileSync(path.join(srcDir, name), 'utf-8') }));
}

function parseLiteral(text: string): unknown {
    const value = text.trim();
    if (value === 'true') { return true; }
    if (value === 'false') { return false; }
    if (/^-?\d+(\.\d+)?$/.test(value)) { return Number(value); }
    const quoted = value.match(/^'(.*)'$/);
    return quoted ? quoted[1] : undefined;
}

describe('package.json contract', () => {
    it('declares every setting the code reads, with the same default', () => {
        const read = /\.get<\w+>\(\s*'(\w+)'\s*(?:,\s*([^)]+?))?\s*\)/g;
        const problems: string[] = [];
        let seen = 0;

        for (const { name, text } of sourceFiles()) {
            for (const match of text.matchAll(read)) {
                seen++;
                const [, key, defaultText] = match;
                const declared = properties[`zoteroMcp.${key}`];
                if (!declared) {
                    problems.push(`${name}: reads undeclared setting zoteroMcp.${key}`);
                    continue;
                }
                const codeDefault = defaultText === undefined ? undefined : parseLiteral(defaultText);
                if (codeDefault !== undefined && codeDefault !== declared.default) {
                    problems.push(`${name}: zoteroMcp.${key} defaults to ${JSON.stringify(codeDefault)} in code but ${JSON.stringify(declared.default)} in package.json`);
                }
            }
        }

        assert.ok(seen > 15, 'the scan found suspiciously few settings reads');
        assert.deepStrictEqual(problems, []);
    });

    it('has no declared setting that the code never reads', () => {
        const sources = sourceFiles().map(file => file.text).join('\n');
        const dead = Object.keys(properties)
            .map(full => full.replace(/^zoteroMcp\./, ''))
            .filter(key => !sources.includes(`'${key}'`));
        assert.deepStrictEqual(dead, []);
    });

    it('requires a VS Code engine no older than the API typings it compiles against', () => {
        const engine = String(manifest.engines.vscode).replace(/^\D+/, '');
        const types = String(manifest.devDependencies['@types/vscode']).replace(/^\D+/, '');
        assert.strictEqual(engine, types);
    });

    it('pins the Keeper archive tag to this extension version', () => {
        assert.ok(
            ZOTERO_KEEPER_SOURCE_URL.endsWith(`/v${manifest.version}-ext.tar.gz`),
            `${ZOTERO_KEEPER_SOURCE_URL} does not match extension ${manifest.version}`,
        );
    });

    it('only lists walkthrough media and icons that exist', () => {
        const media = manifest.contributes.walkthroughs
            .flatMap((w: { steps: Array<{ media: { markdown?: string } }> }) => w.steps.map(s => s.media.markdown))
            .concat(manifest.icon);
        for (const relative of media) {
            assert.ok(fs.existsSync(path.join(extensionRoot, relative)), `missing ${relative}`);
        }
    });
});
