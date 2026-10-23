# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script builds the Exygen monorepo packages
# under `apps/` (`agent`, `api`, `web`) either
# separately, in custom combinations, or all at once
# in sequential order (`agent` -> `api` -> `web`).
#
# Current File: win/build.ps1
# Commands: [all|agent|api|web ...] [--parallel|-p] [--no-cache] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
. (Join-Path $ScriptDir "logs.ps1")

$ErrorActionPreference = "Stop"
$ValidApps = @("agent", "api", "web")

function Show-Usage {
    info "Usage: .\scripts\win\build.ps1 [targets...] [options]"
    info "Targets:"
    info "  all                 Build all packages in sequential order: agent -> api -> web (default)"
    info "  agent               Build apps/agent (Python exygen-agent package)"
    info "  api                 Build apps/api (Python FastAPI exygen-api package)"
    info "  web                 Build apps/web (TypeScript React + TanStack web application)"
    info "Options:"
    info "  --sequential, -s    Build targets one after another in order (default)"
    info "  --parallel, -p      Build targets concurrently via Nx run-many"
    info "  --no-cache          Bypass Nx build cache (--skip-nx-cache)"
    info "  --dry-run           Log the build commands without executing them"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  .\scripts\win\build.ps1"
    info "  .\scripts\win\build.ps1 agent"
    info "  .\scripts\win\build.ps1 agent api"
    info "  .\scripts\win\build.ps1 all --no-cache"
}

function Normalize-Target {
    param([string]$Raw)
    $cleaned = $Raw -replace "^apps[\\/]", "" -replace "[\\/]$", ""
    if ($cleaned -in @("agent", "api", "web", "all")) {
        return $cleaned
    }
    return $null
}

$Mode = "sequential"
$NoCache = $false
$DryRun = $false
$Requested = New-Object System.Collections.Generic.List[string]

foreach ($arg in $args) {
    switch ($arg) {
        { $_ -in @("--help", "-h", "/?") } {
            Show-Usage
            exit 0
        }
        { $_ -in @("--sequential", "-s") } {
            $Mode = "sequential"
        }
        { $_ -in @("--parallel", "-p") } {
            $Mode = "parallel"
        }
        { $_ -in @("--no-cache", "--skip-nx-cache") } {
            $NoCache = $true
        }
        "--dry-run" {
            $DryRun = $true
        }
        "--all" { $Requested.Add("all") }
        "--agent" { $Requested.Add("agent") }
        "--api" { $Requested.Add("api") }
        "--web" { $Requested.Add("web") }
        { $_.StartsWith("-") } {
            error "Unknown option: $arg"
            Show-Usage
            exit 1
        }
        default {
            foreach ($part in ($arg -split ",")) {
                $norm = Normalize-Target $part
                if (-not $norm) {
                    error "Unknown build target: '$part'. Expected one of: all, agent, api, web."
                    exit 1
                }
                $Requested.Add($norm)
            }
        }
    }
}

if ($Requested.Count -eq 0 -or $Requested.Contains("all")) {
    $Targets = $ValidApps
} else {
    $Targets = $Requested | Select-Object -Unique
}

$NxFlags = @()
if ($NoCache) {
    $NxFlags += "--skip-nx-cache"
}

Push-Location $RootDir
try {
    info "Selected build targets ($Mode): $($Targets -join ' ')"

    if ($Mode -eq "parallel" -and $Targets.Count -gt 1) {
        $projectsCsv = $Targets -join ","
        $cmdDisplay = "pnpm nx run-many -t build --projects=$projectsCsv $($NxFlags -join ' ')".Trim()
        if ($DryRun) {
            info "[dry-run] Would run: $cmdDisplay"
            exit 0
        }
        info "Running parallel build for: $projectsCsv"
        & pnpm nx run-many -t build "--projects=$projectsCsv" @NxFlags
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        success "Completed parallel build for: $($Targets -join ' ')"
        exit 0
    }

    $step = 1
    $total = $Targets.Count
    foreach ($app in $Targets) {
        $cmdDisplay = "pnpm nx run ${app}:build $($NxFlags -join ' ')".Trim()
        if ($DryRun) {
            info "[dry-run] ($step/$total) Would build '$app': $cmdDisplay"
        } else {
            info "($step/$total) Building '$app' (apps/$app)..."
            & pnpm nx run "${app}:build" @NxFlags
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            success "($step/$total) Built '$app' successfully."
        }
        $step++
    }

    if ($DryRun) {
        info "Dry-run complete. No packages were built."
    } else {
        success "All requested packages built ($($Targets -join ' '))."
    }
} finally {
    Pop-Location
}
