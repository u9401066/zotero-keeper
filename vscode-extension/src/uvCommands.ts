/**
 * Argument builders for uv invocations shared by the embedded (UvPythonManager)
 * and system-Python (PythonEnvironment) install flows.
 *
 * Arguments are returned as arrays and are meant for execFile (no shell), so
 * paths with spaces or quotes cannot change the command that runs.
 */

/**
 * One uv resolver invocation for packages that must remain compatible.
 * Keeping Zotero Keeper and PubMed Search MCP in the same command prevents an
 * observable MCP SDK 1.x/2.x intermediate state during extension upgrades.
 */
export function buildAtomicPackageInstallArgs(
    pythonBinary: string,
    packages: readonly string[],
): string[] {
    return ['pip', 'install', '--upgrade', '--force-reinstall', '--python', pythonBinary, ...packages];
}
