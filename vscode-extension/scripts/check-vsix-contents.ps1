param(
    [string]$VsixPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$extensionRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$sourceManifestPath = Join-Path $extensionRoot "package.json"
$sourceKeeperPackagePath = Join-Path $extensionRoot "src/zoteroKeeperPackage.ts"
$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
$expectedExtensionVersion = [string]$sourceManifest.version
$sourceKeeperPackage = Get-Content -LiteralPath $sourceKeeperPackagePath -Raw

$keeperVersionMatch = [regex]::Match(
    $sourceKeeperPackage,
    'ZOTERO_KEEPER_VERSION\s*=\s*[''"](?<version>\d+\.\d+\.\d+)[''"]'
)
if (-not $keeperVersionMatch.Success) {
    throw "Cannot find ZOTERO_KEEPER_VERSION in $sourceKeeperPackagePath"
}
$expectedKeeperVersion = $keeperVersionMatch.Groups["version"].Value

$keeperSourceMatch = [regex]::Match(
    $sourceKeeperPackage,
    'ZOTERO_KEEPER_SOURCE_URL\s*=\s*[\r\n ]*[''"](?<url>[^''"]+)[''"]'
)
if (-not $keeperSourceMatch.Success) {
    throw "Cannot find ZOTERO_KEEPER_SOURCE_URL in $sourceKeeperPackagePath"
}
$expectedKeeperSourceUrl = $keeperSourceMatch.Groups["url"].Value
$keeperTagMatch = [regex]::Match(
    $expectedKeeperSourceUrl,
    '/tags/(?<tag>v\d+\.\d+\.\d+-ext)\.tar\.gz'
)
if (-not $keeperTagMatch.Success) {
    throw "ZOTERO_KEEPER_SOURCE_URL does not contain a release archive tag: $expectedKeeperSourceUrl"
}
$expectedKeeperSourceTag = $keeperTagMatch.Groups["tag"].Value
$expectedExtensionTag = "v$expectedExtensionVersion-ext"
if ($expectedKeeperSourceTag -ne $expectedExtensionTag) {
    throw "Keeper source tag mismatch: expected $expectedExtensionTag, got $expectedKeeperSourceTag"
}

if (-not $VsixPath) {
    $latest = Get-ChildItem -LiteralPath . -Filter "vscode-zotero-mcp-*.vsix" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No vscode-zotero-mcp VSIX found in the current directory."
    }
    $VsixPath = $latest.FullName
}

$resolvedVsix = Resolve-Path -LiteralPath $VsixPath
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("zk-vsix-check-" + [System.Guid]::NewGuid().ToString("N"))
$zipPath = Join-Path $tempRoot "extension.zip"
$unpacked = Join-Path $tempRoot "unpacked"

try {
    New-Item -ItemType Directory -Path $tempRoot, $unpacked -Force | Out-Null
    Copy-Item -LiteralPath $resolvedVsix.Path -Destination $zipPath -Force
    Expand-Archive -LiteralPath $zipPath -DestinationPath $unpacked -Force

    $required = @(
        "extension/package.json",
        "extension/readme.md",
        "extension/changelog.md",
        "extension/out/clineMcpConfig.js",
        "extension/out/extension.js",
        "extension/out/pythonEnvironment.js",
        "extension/out/uvPythonManager.js",
        "extension/out/zoteroKeeperPackage.js",
        "extension/resources/walkthrough/python.md",
        "extension/resources/walkthrough/packages.md",
        "extension/resources/repo-assets/keeper/AGENTS.md",
        "extension/resources/repo-assets/keeper/.github/copilot-instructions.md",
        "extension/resources/repo-assets/keeper/.github/zotero-research-workflow.md",
        "extension/resources/repo-assets/keeper/.codex/skills/zotero-keeper-harness/SKILL.md",
        "extension/resources/repo-assets/keeper/.codex/skills/llm-wiki-builder/SKILL.md",
        "extension/resources/repo-assets/keeper/.cline/skills/zotero-keeper-harness/SKILL.md",
        "extension/resources/repo-assets/keeper/.cline/skills/llm-wiki-builder/SKILL.md",
        "extension/resources/repo-assets/keeper/.clinerules/00-zotero-project.md",
        "extension/resources/repo-assets/keeper/.clinerules/10-zotero-python.md",
        "extension/resources/repo-assets/keeper/.clinerules/20-zotero-vscode-extension.md",
        "extension/resources/repo-assets/keeper/.clinerules/30-zotero-research-workflow.md",
        "extension/resources/repo-assets/keeper/.clinerules/35-foam-llm-wiki.md",
        "extension/resources/repo-assets/keeper/.clinerules/40-zotero-release.md",
        "extension/resources/repo-assets/keeper/.clinerules/workflows/zotero-full-check.md",
        "extension/resources/repo-assets/keeper/.clinerules/workflows/llm-wiki-build.md",
        "extension/resources/repo-assets/keeper/.clinerules/workflows/zotero-mcp-setup.md",
        "extension/resources/repo-assets/keeper/.clinerules/workflows/zotero-release-publish.md",
        "extension/resources/repo-assets/keeper/.clinerules/workflows/zotero-skills-audit.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.github/agents/research.agent.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.github/hooks/pipeline-enforcer.json",
        "extension/resources/repo-assets/pubmed-search-mcp/.github/hooks/copilot-tool-policy.json",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/analyze-prompt.ps1",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/analyze-prompt.sh",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/enforce-pipeline.ps1",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/session-init.sh",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/session-init.ps1",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/enforce-pipeline.sh",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/evaluate-results.ps1",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/evaluate-results.sh",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/session-cleanup.ps1",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/session-cleanup.sh",
        "extension/resources/repo-assets/pubmed-search-mcp/scripts/hooks/copilot/hook_runtime.py",
        "extension/resources/repo-assets/pubmed-search-mcp/.codex/skills/pubmed-search-mcp-harness/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.cline/skills/pubmed-search-mcp-harness/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/50-pubmed-project.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/60-pubmed-python.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/70-pubmed-mcp-tools.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/80-pubmed-release.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/workflows/pubmed-full-check.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/workflows/pubmed-mcp-setup.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/workflows/pubmed-release-publish.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.clinerules/workflows/pubmed-skills-audit.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pipeline-persistence/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-export-citations/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-fulltext-access/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-gene-drug-research/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-mcp-tools-reference/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-multi-source-search/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-paper-exploration/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-pico-search/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-quick-search/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-research-chronicle/SKILL.md",
        "extension/resources/repo-assets/pubmed-search-mcp/.claude/skills/pubmed-systematic-search/SKILL.md"
    )

    foreach ($relative in $required) {
        $path = Join-Path $unpacked $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "VSIX is missing required packaged file: $relative"
        }
    }

    $packagedManifestPath = Join-Path $unpacked "extension/package.json"
    $packagedManifest = Get-Content -LiteralPath $packagedManifestPath -Raw | ConvertFrom-Json
    if ([string]$packagedManifest.version -ne $expectedExtensionVersion) {
        throw (
            "Packaged extension version mismatch: expected $expectedExtensionVersion, " +
            "got $($packagedManifest.version)"
        )
    }

    $compiledKeeperPath = Join-Path $unpacked "extension/out/zoteroKeeperPackage.js"
    $compiledKeeper = Get-Content -LiteralPath $compiledKeeperPath -Raw
    $compiledKeeperVersionMatch = [regex]::Match(
        $compiledKeeper,
        'ZOTERO_KEEPER_VERSION\s*=\s*[''"](?<version>\d+\.\d+\.\d+)[''"]'
    )
    if (-not $compiledKeeperVersionMatch.Success) {
        throw "Cannot find compiled ZOTERO_KEEPER_VERSION in extension/out/zoteroKeeperPackage.js"
    }
    $compiledKeeperVersion = $compiledKeeperVersionMatch.Groups["version"].Value
    if ($compiledKeeperVersion -ne $expectedKeeperVersion) {
        throw (
            "Compiled Keeper version mismatch: expected $expectedKeeperVersion, " +
            "got $compiledKeeperVersion"
        )
    }
    $compiledKeeperSourceMatch = [regex]::Match(
        $compiledKeeper,
        'ZOTERO_KEEPER_SOURCE_URL\s*=\s*[''"](?<url>[^''"]+)[''"]'
    )
    if (-not $compiledKeeperSourceMatch.Success) {
        throw "Cannot find compiled ZOTERO_KEEPER_SOURCE_URL in extension/out/zoteroKeeperPackage.js"
    }
    $compiledKeeperSourceUrl = $compiledKeeperSourceMatch.Groups["url"].Value
    if ($compiledKeeperSourceUrl -ne $expectedKeeperSourceUrl) {
        throw (
            "Compiled Keeper source mismatch: expected $expectedKeeperSourceUrl " +
            "got $compiledKeeperSourceUrl"
        )
    }

    $forbiddenPaths = @(
        "extension/resources/agents/research.agent.md"
    )

    foreach ($relative in $forbiddenPaths) {
        $path = Join-Path $unpacked $relative
        if (Test-Path -LiteralPath $path) {
            throw "VSIX still contains removed legacy file: $relative"
        }
    }

    $forbiddenText = @(
        "Python 3.11",
        "blob/HEAD/../",
        "search_pubmed_exclude_owned",
        "quick_import_pmids",
        "import_from_pmids",
        "import_ris_to_zotero",
        "batch_import_from_pubmed"
    )

    $scanRoots = @(
        (Join-Path $unpacked "extension/resources"),
        (Join-Path $unpacked "extension/readme.md"),
        (Join-Path $unpacked "extension/changelog.md"),
        (Join-Path $unpacked "extension/package.json")
    )

    $files = @()
    foreach ($scanRoot in $scanRoots) {
        if (Test-Path -LiteralPath $scanRoot -PathType Leaf) {
            $files += Get-Item -LiteralPath $scanRoot
        } elseif (Test-Path -LiteralPath $scanRoot -PathType Container) {
            $files += Get-ChildItem -LiteralPath $scanRoot -Recurse -File |
                Where-Object { $_.Extension -in @(".md", ".json", ".sh", ".ps1") }
        }
    }

    foreach ($needle in $forbiddenText) {
        $matches = $files | Select-String -SimpleMatch -Pattern $needle
        if ($matches) {
            $first = $matches | Select-Object -First 1
            throw "VSIX contains forbidden text '$needle' at $($first.Path):$($first.LineNumber)"
        }
    }

    Write-Host (
        "VSIX contents check passed: $($resolvedVsix.Path) " +
        "(extension $expectedExtensionVersion, Keeper $expectedKeeperVersion, " +
        "source $expectedKeeperSourceTag)"
    )
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
