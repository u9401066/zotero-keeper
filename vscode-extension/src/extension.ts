/**
 * Zotero + PubMed MCP Extension
 *
 * Provides AI-powered research assistant capabilities by integrating
 * Zotero reference management and PubMed literature search with GitHub Copilot.
 *
 * Self-contained: Downloads Python automatically for non-technical users.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { PythonEnvironment } from './pythonEnvironment';
import { UvPythonManager } from './uvPythonManager';
import { ZoteroMcpServerProvider } from './mcpProvider';
import { StatusBarManager } from './statusBar';
import { installClineMcpServers, isClineInstalled } from './clineMcpConfig';

let pythonEnv: PythonEnvironment;
let uvPython: UvPythonManager;
let mcpProvider: ZoteroMcpServerProvider;
let statusBar: StatusBarManager;
let extensionContext: vscode.ExtensionContext;
let runtimeSyncListenersRegistered = false;

// The resolved Python path (either system or embedded)
let resolvedPythonPath: string | undefined;

// Context keys for walkthrough completion tracking
const CONTEXT_PYTHON_READY = 'zoteroMcp.pythonReady';
const CONTEXT_PACKAGES_READY = 'zoteroMcp.packagesReady';
const CONTEXT_ZOTERO_CONNECTED = 'zoteroMcp.zoteroConnected';
const FIRST_ACTIVATION_KEY = 'zoteroMcp.firstActivation';
const SKILLS_INSTALLED_KEY = 'zoteroMcp.skillsInstalled';

/**
 * Official user-facing PubMed skill names that the extension is allowed to
 * install and manage.  Skills not in this list will be removed during cleanup
 * so that stale directories from older extension versions do not linger.
 */
const PUBMED_USER_SKILL_NAMES: readonly string[] = [
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

/**
 * Official Cline harness skills installed from the bundled Zotero Keeper and
 * PubMed Search MCP repository assets.
 */
const CLINE_HARNESS_SKILL_NAMES: readonly string[] = [
    'zotero-keeper-harness',
    'pubmed-search-mcp-harness',
];

/**
 * Official Codex harness skills installed for Codex-enabled workspaces.
 */
const CODEX_HARNESS_SKILL_NAMES: readonly string[] = [
    'zotero-keeper-harness',
    'pubmed-search-mcp-harness',
];

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Zotero MCP extension is activating...');
    extensionContext = context;

    // Initialize components
    pythonEnv = new PythonEnvironment(context);
    uvPython = new UvPythonManager(context);
    statusBar = new StatusBarManager();

    // Initialize status bar with context for statistics
    statusBar.initialize(context);

    // Register commands first (so they're available even if setup fails)
    registerCommands(context);

    // Show initial status
    statusBar.setStatus('initializing', 'Zotero MCP: Initializing...');

    try {
        // Step 1: Ensure Python is available (try system first, then embedded)
        resolvedPythonPath = await ensurePythonEnvironment();

        if (!resolvedPythonPath) {
            statusBar.setStatus('error', 'Zotero MCP: Python setup failed');
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, false);
            showFirstTimeWalkthrough(context);
            return;
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);

        // Step 2: Check/install required packages (handled by embedded Python if used)
        const packagesReady = await ensurePackagesInstalled();

        if (!packagesReady) {
            statusBar.setStatus('error', 'Zotero MCP: Package install failed');
            await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
            showFirstTimeWalkthrough(context);
            return;
        }
        await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);

        // Step 3: Register MCP provider and synchronize external MCP consumers
        syncRuntimeConsumers(context, resolvedPythonPath, true);

        // Step 4: Check Zotero connection (non-blocking)
        checkAndUpdateZoteroStatus();

        // Step 5: Install official Copilot/Cline assets if needed
        await installCopilotInstructions(context);

        // Step 6: Update status
        statusBar.setStatus('ready', 'Zotero MCP: Ready');

        // Show walkthrough on first activation
        showFirstTimeWalkthrough(context);

        console.log('Zotero MCP extension activated successfully');

    } catch (error) {
        console.error('Zotero MCP activation error:', error);
        statusBar.setStatus('error', 'Zotero MCP: Activation failed');
        vscode.window.showErrorMessage(`Zotero MCP activation failed: ${error}`);
    }
}

/**
 * Ensure Python is available - uses uv-managed Python by default for consistency
 *
 * Priority (when useEmbeddedPython = true, the default):
 *   1. Use uv-managed Python 3.12 (guaranteed compatible, self-contained)
 *   2. Fall back to system Python discovery only if uv setup fails
 *
 * Priority (when useEmbeddedPython = false):
 *   1. Use system Python (user's responsibility to ensure compatibility)
 */
async function ensurePythonEnvironment(): Promise<string | undefined> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const useEmbedded = config.get<boolean>('useEmbeddedPython', true);

    // When useEmbeddedPython is true (default), prioritize uv-managed Python
    // This ensures consistent behavior regardless of user's system Python version
    if (useEmbedded) {
        console.log('Using uv-managed Python (useEmbeddedPython=true)...');
        statusBar.setStatus('installing', 'Zotero MCP: Setting up Python environment...');

        try {
            // UvPythonManager.ensureReady() handles uv download + Python 3.12 install + packages
            const uvPythonPath = await uvPython.ensureReady();
            console.log('uv-managed Python ready:', uvPythonPath);
            return uvPythonPath;
        } catch (error) {
            console.error('Failed to set up Python with uv:', error);

            // Fall back to system Python discovery if uv setup fails. Package
            // installs still use a writable extension-managed venv.
            console.log('Falling back to system Python...');
            const systemPython = await pythonEnv.ensurePython();
            if (systemPython) {
                console.log('Using system Python as fallback:', systemPython);
                vscode.window.showWarningMessage(
                    'Using system Python as fallback. For best results, ensure Python 3.12+ is installed.',
                    'OK'
                );
                return systemPython;
            }

            // Both uv and system Python failed
            vscode.window.showErrorMessage(
                `Failed to set up Python environment: ${error}`,
                'Retry', 'Install Python Manually'
            ).then(choice => {
                if (choice === 'Retry') {
                    vscode.commands.executeCommand('zoteroMcp.setupWizard');
                } else if (choice === 'Install Python Manually') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
                }
            });
            return undefined;
        }
    }

    // When useEmbeddedPython is false, use system Python only
    console.log('Using system Python (useEmbeddedPython=false)...');
    const systemPython = await pythonEnv.ensurePython();

    if (systemPython) {
        console.log('Using system Python:', systemPython);
        return systemPython;
    }

    // No system Python found and embedded is disabled
    vscode.window.showErrorMessage(
        'Python not found. Install Python 3.12+ or enable embedded Python in settings.',
        'Download Python', 'Enable Embedded Python'
    ).then(choice => {
        if (choice === 'Download Python') {
            vscode.env.openExternal(vscode.Uri.parse('https://www.python.org/downloads/'));
        } else if (choice === 'Enable Embedded Python') {
            config.update('useEmbeddedPython', true, vscode.ConfigurationTarget.Global);
            vscode.commands.executeCommand('zoteroMcp.setupWizard');
        }
    });

    return undefined;
}

/**
 * Ensure packages are installed
 */
async function ensurePackagesInstalled(): Promise<boolean> {
    // If using uv-managed Python, packages were installed during setup
    if (uvPython.isReady()) {
        return true;
    }

    // Using system Python - check and install packages
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const autoInstall = config.get<boolean>('autoInstallPackages', true);

    let packagesInstalled = await pythonEnv.checkPackages();

    if (!packagesInstalled) {
        if (autoInstall) {
            statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
            packagesInstalled = await pythonEnv.installPackages();
            resolvedPythonPath = pythonEnv.getPythonPath() || resolvedPythonPath;
        } else {
            const choice = await vscode.window.showInformationMessage(
                'Zotero MCP requires Python packages (zotero-keeper, pubmed-search-mcp). Install now?',
                'Install', 'Later'
            );
            if (choice === 'Install') {
                statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
                packagesInstalled = await pythonEnv.installPackages();
                resolvedPythonPath = pythonEnv.getPythonPath() || resolvedPythonPath;
            }
        }
    }

    return packagesInstalled;
}

/**
 * Register the native VS Code MCP provider once, then only update its Python
 * interpreter when the install flow switches from system Python to a managed venv.
 */
function registerOrUpdateMcpProvider(
    pythonPath: string,
    context: vscode.ExtensionContext = extensionContext
): void {
    if (!mcpProvider) {
        mcpProvider = new ZoteroMcpServerProvider(pythonPath, context);

        const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'zotero-mcp.servers',
            mcpProvider
        );
        context.subscriptions.push(providerDisposable);
        return;
    }

    mcpProvider.setPythonPath(pythonPath);
}

function syncClineConfiguration(
    context: vscode.ExtensionContext,
    pythonPath: string,
    notifyUser: boolean = false
): void {
    if (!isClineInstalled(context)) {
        return;
    }

    try {
        const updated = installClineMcpServers(context, pythonPath);
        if (updated) {
            console.log('Cline MCP servers configured/updated');
            if (notifyUser) {
                vscode.window.showInformationMessage(
                    'Zotero + PubMed MCP servers have been added to Cline. Restart Cline to use them.',
                    'OK'
                );
            }
        }
    } catch (error) {
        console.error('Failed to configure Cline MCP servers:', error);
    }
}

function syncRuntimeConsumers(
    context: vscode.ExtensionContext,
    pythonPath: string,
    notifyCline: boolean = false
): void {
    registerOrUpdateMcpProvider(pythonPath, context);
    syncClineConfiguration(context, pythonPath, notifyCline);
    registerRuntimeSyncListeners(context);
}

function registerRuntimeSyncListeners(context: vscode.ExtensionContext): void {
    if (runtimeSyncListenersRegistered) {
        return;
    }

    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((event) => {
            if (!event.affectsConfiguration('zoteroMcp') || !resolvedPythonPath) {
                return;
            }

            syncRuntimeConsumers(context, resolvedPythonPath);
        })
    );

    context.subscriptions.push(
        vscode.workspace.onDidChangeWorkspaceFolders(() => {
            if (!resolvedPythonPath) {
                return;
            }

            syncRuntimeConsumers(context, resolvedPythonPath);
        })
    );

    runtimeSyncListenersRegistered = true;
}

/**
 * Show walkthrough on first activation
 */
function showFirstTimeWalkthrough(context: vscode.ExtensionContext): void {
    const isFirstActivation = context.globalState.get<boolean>(FIRST_ACTIVATION_KEY, true);

    if (isFirstActivation) {
        // Mark as not first time anymore
        context.globalState.update(FIRST_ACTIVATION_KEY, false);

        // Open walkthrough
        vscode.commands.executeCommand(
            'workbench.action.openWalkthrough',
            'u9401066.vscode-zotero-mcp#zoteroMcp.welcome',
            false
        );
    }
}

/**
 * Check Zotero connection and update context
 */
async function checkAndUpdateZoteroStatus(): Promise<boolean> {
    const connected = await checkZoteroConnection();
    await vscode.commands.executeCommand('setContext', CONTEXT_ZOTERO_CONNECTED, connected);
    return connected;
}

type InstallMode = 'auto' | 'manual';

interface InstallSummary {
    installed: number;
    updated: number;
    preserved: number;
    missingSources: string[];
}

function createInstallSummary(): InstallSummary {
    return {
        installed: 0,
        updated: 0,
        preserved: 0,
        missingSources: [],
    };
}

function getBundledAssetPath(context: vscode.ExtensionContext, ...segments: string[]): string {
    return path.join(context.extensionPath, 'resources', 'repo-assets', ...segments);
}

function ensureParentDirectory(filePath: string): void {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function readUtf8IfExists(filePath: string): string | undefined {
    if (!fs.existsSync(filePath)) {
        return undefined;
    }

    return fs.readFileSync(filePath, 'utf-8');
}

function isKeeperInstructionsFile(content: string): boolean {
    return content.includes('# Copilot User Instructions for Zotero + PubMed MCP')
        || content.includes('# Copilot Instructions for Zotero + PubMed MCP')
        || content.includes('# Copilot 自定義指令 - Zotero Keeper');
}

function isKeeperWorkflowFile(content: string): boolean {
    return content.includes('# Research Workflow Guide for Copilot')
        && content.includes('Zotero + PubMed MCP tools');
}

function isKeeperCodexAgentsFile(content: string): boolean {
    return content.includes('# Zotero + PubMed MCP Codex Harness')
        && content.includes('PubMed Search MCP through the VS Code extension');
}

function copyBundledFile(sourcePath: string, destinationPath: string): boolean {
    ensureParentDirectory(destinationPath);

    if (fs.existsSync(destinationPath)) {
        const current = fs.readFileSync(destinationPath, 'utf-8');
        const incoming = fs.readFileSync(sourcePath, 'utf-8');
        if (current === incoming) {
            return false;
        }
    }

    fs.copyFileSync(sourcePath, destinationPath);
    return true;
}

function collectFilesRecursive(rootDir: string): string[] {
    const files: string[] = [];

    for (const entry of fs.readdirSync(rootDir, { withFileTypes: true })) {
        const fullPath = path.join(rootDir, entry.name);
        if (entry.isDirectory()) {
            files.push(...collectFilesRecursive(fullPath));
        } else {
            files.push(fullPath);
        }
    }

    return files;
}

function syncManagedDirectory(
    sourceDir: string,
    destinationDir: string,
    summary: InstallSummary,
    overwriteExisting: boolean
): void {
    if (!fs.existsSync(sourceDir)) {
        summary.missingSources.push(sourceDir);
        return;
    }

    for (const sourceFile of collectFilesRecursive(sourceDir)) {
        const relativePath = path.relative(sourceDir, sourceFile);
        const destinationFile = path.join(destinationDir, relativePath);
        const alreadyExists = fs.existsSync(destinationFile);

        if (alreadyExists && !overwriteExisting) {
            continue;
        }

        if (!copyBundledFile(sourceFile, destinationFile)) {
            continue;
        }

        if (alreadyExists) {
            summary.updated++;
        } else {
            summary.installed++;
        }
    }
}

function syncSkillDirectories(
    sourceRoot: string,
    destinationRoot: string,
    summary: InstallSummary,
    overwriteExisting: boolean
): void {
    if (!fs.existsSync(sourceRoot)) {
        summary.missingSources.push(sourceRoot);
        return;
    }

    for (const entry of fs.readdirSync(sourceRoot, { withFileTypes: true })) {
        if (!entry.isDirectory()) {
            continue;
        }

        syncManagedDirectory(
            path.join(sourceRoot, entry.name),
            path.join(destinationRoot, entry.name),
            summary,
            overwriteExisting
        );
    }
}

/**
 * Remove legacy files from older extension versions that are no longer
 * distributed.  Safe to call even if the files do not exist.
 */
function cleanupLegacyAssets(workspaceRoot: string, summary: InstallSummary): void {
    const githubDir = path.join(workspaceRoot, '.github');

    // v0.5.13 and earlier installed simplified markdown files from
    // resources/skills/ which have been replaced by official repo assets.
    const legacyFiles = [
        // Old simplified copilot instructions (replaced by repo-assets/keeper/.github/copilot-instructions.md)
        path.join(githubDir, 'copilot-instructions.md.old'),
        // Old simplified research workflow (replaced by repo-assets/keeper/.github/zotero-research-workflow.md)
        path.join(githubDir, 'zotero-research-workflow.md.old'),
    ];

    for (const legacyFile of legacyFiles) {
        if (fs.existsSync(legacyFile)) {
            fs.unlinkSync(legacyFile);
            summary.updated++;
        }
    }

    // The old extension also installed two files directly from resources/skills/:
    //   .github/copilot-instructions.md  (simplified, not the official repo version)
    //   .github/zotero-research-workflow.md  (simplified)
    // These are now replaced by the official repo-asset versions above,
    // so no separate cleanup is needed — they get overwritten in the main flow.
}

/**
 * Remove skill directories that are no longer in the official allowlist.
 * This prevents stale skills from lingering after an extension upgrade.
 */
function cleanupStaleSkills(
    destinationRoot: string,
    allowedSkillNames: readonly string[],
    summary: InstallSummary
): void {
    if (!fs.existsSync(destinationRoot)) {
        return;
    }

    for (const entry of fs.readdirSync(destinationRoot, { withFileTypes: true })) {
        if (!entry.isDirectory()) {
            continue;
        }

        // Only clean up pubmed-* and pipeline-* directories that we manage
        const isManaged = entry.name.startsWith('pubmed-') || entry.name.startsWith('pipeline-');
        if (!isManaged) {
            continue;
        }

        if (!allowedSkillNames.includes(entry.name)) {
            const staleDir = path.join(destinationRoot, entry.name);
            fs.rmSync(staleDir, { recursive: true, force: true });
            summary.updated++;
        }
    }
}

/**
 * Install official assistant assets from bundled keeper/pubmed repository files.
 * IMPORTANT: Never overwrite existing user instructions automatically.
 */
async function installCopilotInstructions(
    context: vscode.ExtensionContext,
    mode: InstallMode = 'auto'
): Promise<void> {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        if (mode === 'manual') {
            vscode.window.showWarningMessage('Please open a workspace folder first.');
        }
        return;
    }

    const workspaceRoot = workspaceFolder.uri.fsPath;
    const githubDir = path.join(workspaceRoot, '.github');
    const skillsDir = path.join(workspaceRoot, '.claude', 'skills');
    const codexSkillsDir = path.join(workspaceRoot, '.codex', 'skills');
    const clineSkillsDir = path.join(workspaceRoot, '.cline', 'skills');
    const clineRulesDir = path.join(workspaceRoot, '.clinerules');
    const agentsDir = path.join(githubDir, 'agents');
    const hooksDir = path.join(githubDir, 'hooks');
    const copilotScriptsDir = path.join(workspaceRoot, 'scripts', 'hooks', 'copilot');

    const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
    const workflowDest = path.join(githubDir, 'zotero-research-workflow.md');
    const codexAgentsPath = path.join(workspaceRoot, 'AGENTS.md');

    const keeperInstructions = getBundledAssetPath(context, 'keeper', '.github', 'copilot-instructions.md');
    const keeperWorkflow = getBundledAssetPath(context, 'keeper', '.github', 'zotero-research-workflow.md');
    const keeperCodexAgents = getBundledAssetPath(context, 'keeper', 'AGENTS.md');
    const keeperCodexSkills = getBundledAssetPath(context, 'keeper', '.codex', 'skills');
    const keeperClineSkills = getBundledAssetPath(context, 'keeper', '.cline', 'skills');
    const keeperClineRules = getBundledAssetPath(context, 'keeper', '.clinerules');
    const pubmedSkills = getBundledAssetPath(context, 'pubmed-search-mcp', '.claude', 'skills');
    const pubmedCodexSkills = getBundledAssetPath(context, 'pubmed-search-mcp', '.codex', 'skills');
    const pubmedClineSkills = getBundledAssetPath(context, 'pubmed-search-mcp', '.cline', 'skills');
    const pubmedClineRules = getBundledAssetPath(context, 'pubmed-search-mcp', '.clinerules');
    const pubmedAgents = getBundledAssetPath(context, 'pubmed-search-mcp', '.github', 'agents');
    const pubmedHooks = getBundledAssetPath(context, 'pubmed-search-mcp', '.github', 'hooks');
    const pubmedCopilotScripts = getBundledAssetPath(context, 'pubmed-search-mcp', 'scripts', 'hooks', 'copilot');

    const summary = createInstallSummary();
    const managedAgentPath = path.join(agentsDir, 'research.agent.md');
    const managedClineSkillPath = path.join(clineSkillsDir, CLINE_HARNESS_SKILL_NAMES[0], 'SKILL.md');
    const managedCodexSkillPath = path.join(codexSkillsDir, CODEX_HARNESS_SKILL_NAMES[0], 'SKILL.md');
    const hasManagedAssets = fs.existsSync(workflowDest)
        || fs.existsSync(managedAgentPath)
        || fs.existsSync(managedClineSkillPath)
        || fs.existsSync(managedCodexSkillPath)
        || fs.existsSync(codexAgentsPath);

    if (mode === 'manual') {
        const choice = await vscode.window.showInformationMessage(
            'Install/update curated official Copilot, Codex, and Cline assets from Zotero Keeper and PubMed Search MCP? Existing custom instructions will be preserved.',
            'Install',
            'Cancel'
        );

        if (choice !== 'Install') {
            return;
        }
    }

    const existingInstructions = readUtf8IfExists(instructionsPath);
    const hasCustomInstructions = !!existingInstructions && !isKeeperInstructionsFile(existingInstructions);
    const existingCodexAgents = readUtf8IfExists(codexAgentsPath);
    const hasCustomCodexAgents = !!existingCodexAgents && !isKeeperCodexAgentsFile(existingCodexAgents);

    if (mode === 'auto' && (hasCustomInstructions || hasCustomCodexAgents) && !hasManagedAssets) {
        const choice = await vscode.window.showInformationMessage(
            'Install curated user-facing Zotero + PubMed Copilot/Codex/Cline assets? Existing custom instructions will be preserved.',
            'Yes',
            'No'
        );

        if (choice !== 'Yes') {
            return;
        }
    }

    try {
        // Clean up legacy assets from older extension versions
        cleanupLegacyAssets(workspaceRoot, summary);

        if (!fs.existsSync(keeperInstructions)) {
            summary.missingSources.push(keeperInstructions);
        } else if (!existingInstructions) {
            copyBundledFile(keeperInstructions, instructionsPath);
            summary.installed++;
        } else if (isKeeperInstructionsFile(existingInstructions)) {
            // Always update our own official instructions (auto + manual)
            // so that users who installed an older extension version get
            // the latest collaboration-safe workflow automatically.
            copyBundledFile(keeperInstructions, instructionsPath);
            summary.updated++;
        } else {
            summary.preserved++;
        }

        if (!fs.existsSync(keeperCodexAgents)) {
            summary.missingSources.push(keeperCodexAgents);
        } else if (!existingCodexAgents) {
            copyBundledFile(keeperCodexAgents, codexAgentsPath);
            summary.installed++;
        } else if (isKeeperCodexAgentsFile(existingCodexAgents)) {
            copyBundledFile(keeperCodexAgents, codexAgentsPath);
            summary.updated++;
        } else if (mode === 'manual') {
            const choice = await vscode.window.showWarningMessage(
                'AGENTS.md has been modified. Update it to the latest official Codex harness?',
                'Update',
                'Keep Mine'
            );

            if (choice === 'Update') {
                copyBundledFile(keeperCodexAgents, codexAgentsPath);
                summary.updated++;
            } else {
                summary.preserved++;
            }
        } else {
            summary.preserved++;
        }

        const existingWorkflow = readUtf8IfExists(workflowDest);
        if (!fs.existsSync(keeperWorkflow)) {
            summary.missingSources.push(keeperWorkflow);
        } else if (!existingWorkflow) {
            copyBundledFile(keeperWorkflow, workflowDest);
            summary.installed++;
        } else if (isKeeperWorkflowFile(existingWorkflow)) {
            // Always update our own official workflow (auto + manual)
            // so that legacy tool references are replaced with the new
            // collaboration-safe import_articles workflow.
            copyBundledFile(keeperWorkflow, workflowDest);
            summary.updated++;
        } else if (mode === 'manual') {
            const choice = await vscode.window.showWarningMessage(
                'zotero-research-workflow.md has been modified. Update it to the latest official version?',
                'Update',
                'Keep Mine'
            );

            if (choice === 'Update') {
                copyBundledFile(keeperWorkflow, workflowDest);
                summary.updated++;
            } else {
                summary.preserved++;
            }
        } else {
            summary.preserved++;
        }

        // Remove stale skill directories that are no longer in the official allowlist
        cleanupStaleSkills(skillsDir, PUBMED_USER_SKILL_NAMES, summary);

        syncSkillDirectories(pubmedSkills, skillsDir, summary, true);

        syncSkillDirectories(keeperCodexSkills, codexSkillsDir, summary, true);
        syncSkillDirectories(pubmedCodexSkills, codexSkillsDir, summary, true);
        syncSkillDirectories(keeperClineSkills, clineSkillsDir, summary, true);
        syncSkillDirectories(pubmedClineSkills, clineSkillsDir, summary, true);
        syncManagedDirectory(keeperClineRules, clineRulesDir, summary, true);
        syncManagedDirectory(pubmedClineRules, clineRulesDir, summary, true);

        syncManagedDirectory(pubmedAgents, agentsDir, summary, true);
        syncManagedDirectory(pubmedHooks, hooksDir, summary, true);
        syncManagedDirectory(pubmedCopilotScripts, copilotScriptsDir, summary, true);

        await context.globalState.update(SKILLS_INSTALLED_KEY, true);

        if (mode === 'manual') {
            if (summary.missingSources.length > 0) {
                vscode.window.showWarningMessage(
                    `Installed ${summary.installed} and updated ${summary.updated} assistant asset(s), but ${summary.missingSources.length} bundled source path(s) were missing.`
                );
            } else if (summary.installed > 0 || summary.updated > 0) {
                const details: string[] = [];
                if (summary.preserved > 0) {
                    details.push(`${summary.preserved} preserved`);
                }

                const suffix = details.length > 0 ? ` (${details.join(', ')})` : '';
                vscode.window.showInformationMessage(
                    `Installed ${summary.installed} and updated ${summary.updated} official assistant asset(s)${suffix}.`
                );
            } else if (summary.preserved > 0) {
                vscode.window.showInformationMessage(
                    `No official assets changed. Preserved ${summary.preserved} custom file(s).`
                );
            } else {
                vscode.window.showInformationMessage('No official assistant assets needed updating.');
            }
        }
    } catch (error) {
        console.error('Failed to install official assistant assets:', error);
        if (mode === 'manual') {
            vscode.window.showErrorMessage(`Failed to install official assistant assets: ${error}`);
        }
    }
}

/**
 * Register extension commands
 */
function registerCommands(context: vscode.ExtensionContext): void {
    // Setup Wizard - one-click setup
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.setupWizard', async () => {
            await runSetupWizard();
        })
    );

    // Check Zotero connection
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.checkConnection', async () => {
            const connected = await checkAndUpdateZoteroStatus();
            if (connected) {
                vscode.window.showInformationMessage('✅ Zotero is running and accessible!');
            } else {
                const config = vscode.workspace.getConfiguration('zoteroMcp');
                const host = config.get<string>('zoteroHost', 'localhost');
                const port = config.get<number>('zoteroPort', 23119);
                const choice = await vscode.window.showWarningMessage(
                    `❌ Cannot connect to Zotero at ${host}:${port}. Make sure Zotero is running.`,
                    'Retry', 'Download Zotero', 'Open Settings'
                );
                if (choice === 'Retry') {
                    vscode.commands.executeCommand('zoteroMcp.checkConnection');
                } else if (choice === 'Download Zotero') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.zotero.org/download/'));
                } else if (choice === 'Open Settings') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp.zotero');
                }
            }
        })
    );

    // Install packages
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.installPackages', async () => {
            statusBar.setStatus('installing', 'Zotero MCP: Installing packages...');
            if (!resolvedPythonPath) {
                resolvedPythonPath = await ensurePythonEnvironment();
            }
            const success = await ensurePackagesInstalled();
            if (success) {
                if (resolvedPythonPath) {
                    syncRuntimeConsumers(context, resolvedPythonPath, true);
                }
                statusBar.setStatus('ready', 'Zotero MCP: Ready');
                await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);
                vscode.window.showInformationMessage('✅ Python packages installed successfully!');
                // Refresh MCP servers
                mcpProvider?.refresh();
            } else {
                statusBar.setStatus('error', 'Zotero MCP: Install failed');
                await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, false);
                vscode.window.showErrorMessage('❌ Failed to install packages. Check the output for details.');
            }
        })
    );

    // Show status
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.showStatus', async () => {
            const status = await getExtensionStatus();
            const panel = vscode.window.createWebviewPanel(
                'zoteroMcpStatus',
                'Zotero MCP Status',
                vscode.ViewColumn.One,
                {}
            );
            panel.webview.html = getStatusWebviewContent(status);
        })
    );

    // Open settings
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'zoteroMcp');
        })
    );

    // Open Zotero application
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.openZotero', async () => {
            // Try to open Zotero via URL scheme (works on most platforms)
            vscode.env.openExternal(vscode.Uri.parse('zotero://'));
        })
    );

    // Reinstall embedded Python
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.reinstallPython', async () => {
            const confirm = await vscode.window.showWarningMessage(
                'This will remove and reinstall the embedded Python environment. Continue?',
                'Yes', 'No'
            );

            if (confirm === 'Yes') {
                statusBar.setStatus('installing', 'Zotero MCP: Reinstalling Python...');

                try {
                    await uvPython.cleanup();
                    const newPath = await uvPython.ensureReady();

                    if (newPath) {
                        resolvedPythonPath = newPath;
                        syncRuntimeConsumers(context, newPath, true);
                        statusBar.setStatus('ready', 'Zotero MCP: Ready');
                        vscode.window.showInformationMessage('✅ Python environment reinstalled successfully!');
                    }
                } catch (error) {
                    statusBar.setStatus('error', 'Zotero MCP: Reinstall failed');
                    vscode.window.showErrorMessage(`Failed to reinstall: ${error}`);
                }
            }
        })
    );

    // Install/update official Copilot and Cline assets
    context.subscriptions.push(
        vscode.commands.registerCommand('zoteroMcp.installSkills', async () => {
            await installCopilotInstructions(context, 'manual');
        })
    );
}

/**
 * Run setup wizard - handles all setup in one go
 */
async function runSetupWizard(): Promise<void> {
    const progress = await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Zotero MCP Setup',
            cancellable: false
        },
        async (progress) => {
            // Step 1: Check/setup Python
            progress.report({ message: 'Setting up Python environment...', increment: 0 });

            const pythonPath = await ensurePythonEnvironment();
            if (!pythonPath) {
                return false;
            }
            resolvedPythonPath = pythonPath;
            await vscode.commands.executeCommand('setContext', CONTEXT_PYTHON_READY, true);
            progress.report({ message: 'Python OK ✓', increment: 33 });

            // Step 2: Ensure packages are installed
            progress.report({ message: 'Checking Python packages...', increment: 0 });
            const packagesOk = await ensurePackagesInstalled();
            if (!packagesOk) {
                vscode.window.showErrorMessage('Failed to install Python packages. Check the output panel.');
                return false;
            }
            await vscode.commands.executeCommand('setContext', CONTEXT_PACKAGES_READY, true);
            progress.report({ message: 'Packages OK ✓', increment: 33 });

            // Step 3: Check Zotero
            progress.report({ message: 'Checking Zotero connection...', increment: 34 });
            const zoteroOk = await checkAndUpdateZoteroStatus();

            if (!zoteroOk) {
                const choice = await vscode.window.showWarningMessage(
                    'Zotero is not running. Start Zotero to enable full functionality.',
                    'Download Zotero', 'Continue Anyway'
                );
                if (choice === 'Download Zotero') {
                    vscode.env.openExternal(vscode.Uri.parse('https://www.zotero.org/download/'));
                }
            }

            return true;
        }
    );

    if (progress) {
        if (resolvedPythonPath) {
            syncRuntimeConsumers(extensionContext, resolvedPythonPath, true);
        }

        // Refresh MCP provider
        mcpProvider?.refresh();

        statusBar.setStatus('ready', 'Zotero MCP: Ready');

        vscode.window.showInformationMessage(
            '🎉 Zotero MCP is ready! Try asking Copilot to search PubMed.',
            'Open Copilot Chat'
        ).then(choice => {
            if (choice === 'Open Copilot Chat') {
                vscode.commands.executeCommand('workbench.action.chat.open');
            }
        });
    }
}

/**
 * Check if Zotero is accessible
 */
async function checkZoteroConnection(): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const host = config.get<string>('zoteroHost', 'localhost');
    const port = config.get<number>('zoteroPort', 23119);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
        const response = await fetch(`http://${host}:${port}/connector/ping`, {
            signal: controller.signal,
        });
        const text = await response.text();
        const ok = text.includes('Zotero is running');
        if (!ok) {
            console.warn(`Zotero ping responded but unexpected body: ${text.substring(0, 200)}`);
        }
        return ok;
    } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.warn(`Zotero connection check failed (${host}:${port}): ${msg}`);
        return false;
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Get extension status information
 */
async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('zoteroMcp');
    const isUvManaged = uvPython.isReady();

    return {
        pythonPath: resolvedPythonPath || 'Not configured',
        pythonVersion: isUvManaged
            ? await uvPython.getPythonVersion() || 'Unknown'
            : await pythonEnv.getPythonVersion() || 'Unknown',
        pythonType: isUvManaged ? 'uv-managed (self-contained)' : 'System',
        packagesInstalled: isUvManaged ? true : await pythonEnv.checkPackages(),
        zoteroConnected: await checkZoteroConnection(),
        zoteroHost: config.get<string>('zoteroHost', 'localhost'),
        zoteroPort: config.get<number>('zoteroPort', 23119),
        enabledServers: {
            zoteroKeeper: config.get<boolean>('enableZoteroKeeper', true),
            pubmedSearch: config.get<boolean>('enablePubmedSearch', true),
        }
    };
}

interface ExtensionStatus {
    pythonPath: string;
    pythonVersion: string;
    pythonType: string;
    packagesInstalled: boolean;
    zoteroConnected: boolean;
    zoteroHost: string;
    zoteroPort: number;
    enabledServers: {
        zoteroKeeper: boolean;
        pubmedSearch: boolean;
    };
}

/**
 * Generate status webview HTML
 */
function getStatusWebviewContent(status: ExtensionStatus): string {
    const checkmark = '✅';
    const cross = '❌';

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zotero MCP Status</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        h1 { color: var(--vscode-titleBar-activeForeground); }
        .section {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .section h2 {
            margin-top: 0;
            font-size: 14px;
            color: var(--vscode-descriptionForeground);
        }
        .item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }
        .status { font-weight: bold; }
        .ok { color: #4caf50; }
        .error { color: #f44336; }
        .info { color: #2196f3; }
    </style>
</head>
<body>
    <h1>🔬 Zotero + PubMed MCP Status</h1>

    <div class="section">
        <h2>Python Environment</h2>
        <div class="item">
            <span>Type:</span>
            <span class="info">${status.pythonType}</span>
        </div>
        <div class="item">
            <span>Python Path:</span>
            <span style="font-size: 12px; word-break: break-all;">${status.pythonPath}</span>
        </div>
        <div class="item">
            <span>Python Version:</span>
            <span>${status.pythonVersion}</span>
        </div>
        <div class="item">
            <span>Packages Installed:</span>
            <span class="status ${status.packagesInstalled ? 'ok' : 'error'}">
                ${status.packagesInstalled ? checkmark : cross}
            </span>
        </div>
    </div>

    <div class="section">
        <h2>Zotero Connection</h2>
        <div class="item">
            <span>Host:</span>
            <span>${status.zoteroHost}:${status.zoteroPort}</span>
        </div>
        <div class="item">
            <span>Connected:</span>
            <span class="status ${status.zoteroConnected ? 'ok' : 'error'}">
                ${status.zoteroConnected ? checkmark : cross}
            </span>
        </div>
    </div>

    <div class="section">
        <h2>MCP Servers</h2>
        <div class="item">
            <span>Zotero Keeper:</span>
            <span class="status ${status.enabledServers.zoteroKeeper ? 'ok' : 'error'}">
                ${status.enabledServers.zoteroKeeper ? 'Enabled' : 'Disabled'}
            </span>
        </div>
        <div class="item">
            <span>PubMed Search:</span>
            <span class="status ${status.enabledServers.pubmedSearch ? 'ok' : 'error'}">
                ${status.enabledServers.pubmedSearch ? 'Enabled' : 'Disabled'}
            </span>
        </div>
    </div>
</body>
</html>`;
}

/**
 * Extension deactivation
 */
export function deactivate(): void {
    console.log('Zotero MCP extension is deactivating...');
    statusBar?.dispose();
}
