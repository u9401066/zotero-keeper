/**
 * Test setup — ensure 'vscode' module resolves to our mock.
 *
 * The __mocks__/vscode/ directory is added to NODE_PATH via the test script
 * so that `require('vscode')` / `import 'vscode'` resolves to mock-vscode.
 *
 * This file can be used for additional global test setup if needed.
 */

// Intentionally empty — the mock is resolved via NODE_PATH
// configured in the npm test script.
export {};
