# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script removes build and cache artifacts from
# the entire Exygen codebase or from specific app
# folders under `apps/` (`agent`, `api`, `web`).
# It never descends into `.git` directories.
#
# Current File: win/clean.ps1
# Commands: [all|agent|api|web|path ...] [--dry-run] [--yes|-y] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
. (Join-Path $ScriptDir "logs.ps1")

$ErrorActionPreference = "Stop"

$ArtifactDirs = @(
    "node_modules", ".npm", ".yarn", ".pnp", ".nx",
    "dist", "build", "out", ".output", ".vinxi",
    ".vite", "vite-temp", ".tanstack", ".wrangler", ".mf",
    ".tsbuildinfo", "coverage", ".vitest", ".nyc_output",
    ".biome", ".eslintcache",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    ".hypothesis", "htmlcov", ".tox", ".eggs", ".venv", "venv", "env", ".env_dir",
    ".cache", ".parcel-cache", ".turbo", ".next", ".nuxt", ".svelte-kit",
    "storybook-static", ".storybook-out"
)

function Show-Usage {
    info "Usage: .\scripts\win\clean.ps1 [targets...] [options]"
    info "Targets:"
    info "  all, .              Clean artifacts across the entire repository (default)"
    info "  agent               Clean artifacts in apps/agent (and dist/apps/agent)"
    info "  api                 Clean artifacts in apps/api (and dist/apps/api)"
    info "  web                 Clean artifacts in apps/web (and dist/apps/web)"
    info "  <path>              Clean artifacts in a specific directory path"
    info "Options:"
    info "  --dry-run           List directories that would be deleted without removing them"
    info "  --yes, -y           Skip confirmation prompt"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  .\scripts\win\clean.ps1 --dry-run"
    info "  .\scripts\win\clean.ps1 web --yes"
    info "  .\scripts\win\clean.ps1 agent api -y"
}

function Resolve-ScanRoots {
    param([string]$ArgValue)
    $cleaned = $ArgValue -replace "^apps[\\/]", "" -replace "[\\/]$", ""
    $roots = New-Object System.Collections.Generic.List[string]

    if ($ArgValue -in @("all", ".")) {
        $roots.Add($RootDir)
        return $roots
    }

    if ($cleaned -in @("agent", "api", "web")) {
        $roots.Add((Join-Path $RootDir "apps\$cleaned"))
        $distApp = Join-Path $RootDir "dist\apps\$cleaned"
        if (Test-Path $distApp) {
            $roots.Add($distApp)
        }
        return $roots
    }

    if (Test-Path $ArgValue -PathType Container) {
        $roots.Add((Resolve-Path $ArgValue).Path)
        return $roots
    }

    $candidate = Join-Path $RootDir $ArgValue
    if (Test-Path $candidate -PathType Container) {
        $roots.Add((Resolve-Path $candidate).Path)
        return $roots
    }

    return $null
}

function Find-ArtifactDirectories {
    param([string]$ScanDir)
    $found = New-Object System.Collections.Generic.List[string]
    $distPrefix = Join-Path $RootDir "dist\apps\"

    if ($ScanDir.StartsWith($distPrefix) -and (Test-Path $ScanDir)) {
        $found.Add($ScanDir)
        return $found
    }

    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push($ScanDir)

    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        $children = Get-ChildItem -LiteralPath $current -Directory -Force -ErrorAction SilentlyContinue
        foreach ($child in $children) {
            if ($child.Name -in @(".git", ".hg", ".svn")) {
                continue
            }
            if ($child.Name -in $ArtifactDirs -or $child.Name -like "*.egg-info" -or $child.Name -like "*.dist-info") {
                $found.Add($child.FullName)
                continue
            }
            $stack.Push($child.FullName)
        }
    }
    return $found
}

$DryRun = $false
$SkipConfirm = $false
$RawTargets = New-Object System.Collections.Generic.List[string]

foreach ($arg in $args) {
    switch ($arg) {
        { $_ -in @("--help", "-h", "/?") } {
            Show-Usage
            exit 0
        }
        "--dry-run" { $DryRun = $true }
        { $_ -in @("--yes", "-y") } { $SkipConfirm = $true }
        "--all" { $RawTargets.Add("all") }
        "--agent" { $RawTargets.Add("agent") }
        "--api" { $RawTargets.Add("api") }
        "--web" { $RawTargets.Add("web") }
        { $_.StartsWith("-") } {
            error "Unknown option: $arg"
            Show-Usage
            exit 1
        }
        default {
            foreach ($part in ($arg -split ",")) {
                $RawTargets.Add($part)
            }
        }
    }
}

if ($RawTargets.Count -eq 0) {
    $RawTargets.Add("all")
}

$ScanRoots = New-Object System.Collections.Generic.List[string]
foreach ($raw in $RawTargets) {
    $resolved = Resolve-ScanRoots $raw
    if ($null -eq $resolved) {
        error "'$raw' is not a valid app name (agent, api, web, all) or directory."
        exit 1
    }
    foreach ($r in $resolved) {
        if (-not $ScanRoots.Contains($r)) {
            $ScanRoots.Add($r)
        }
    }
}

$Targets = New-Object System.Collections.Generic.List[string]
foreach ($root in $ScanRoots) {
    info "Scanning: $root"
    foreach ($dir in (Find-ArtifactDirectories $root)) {
        if (-not $Targets.Contains($dir)) {
            $Targets.Add($dir)
        }
    }
}

if ($Targets.Count -eq 0) {
    info "Nothing to clean up."
    exit 0
}

$word = if ($Targets.Count -eq 1) { "directory" } else { "directories" }
info "Found $($Targets.Count) $word to remove:"
foreach ($t in $Targets) {
    info "  - $t"
}

if ($DryRun) {
    info "Dry-run was set, nothing was deleted."
    exit 0
}

if (-not $SkipConfirm) {
    $answer = Read-Host "Delete all of the above? [y/N]"
    if ($answer -notmatch "^(y|yes)$") {
        info "Aborted."
        exit 0
    }
}

$removed = 0
$errors = 0
foreach ($path in $Targets) {
    try {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction Stop
        $removed++
    } catch {
        warn "Could not remove: $path"
        $errors++
    }
}

$doneWord = if ($removed -eq 1) { "directory" } else { "directories" }
if ($errors -gt 0) {
    warn "Removed $removed $doneWord. $errors error(s), see output above."
} else {
    success "Removed $removed $doneWord."
}
