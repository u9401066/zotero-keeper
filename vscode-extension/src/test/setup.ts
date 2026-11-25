/**
 * Test setup — ensure 'vscode' resolves to our compiled mock directory.
 *
 * This is done here instead of in the npm script so the test runner stays
 * cross-platform and does not depend on shell-specific environment syntax.
 */

import Module from 'module';
import * as os from 'os';
import * as path from 'path';

// No test may reach the developer's real Claude Code state file: point Claude
// Code at a directory that does not exist (tests that need one set their own).
process.env.CLAUDE_CONFIG_DIR = path.join(os.tmpdir(), `zotero-mcp-tests-no-claude-${process.pid}`);

const mockPath = path.resolve(__dirname, '__mocks__');
process.env.NODE_PATH = process.env.NODE_PATH
	? `${mockPath}${path.delimiter}${process.env.NODE_PATH}`
	: mockPath;

type ModuleLoaderWithInitPaths = typeof Module & {
	_initPaths(): void;
};

(Module as ModuleLoaderWithInitPaths)._initPaths();

export {};
