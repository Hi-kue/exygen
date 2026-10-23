# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script initializes local environment files
# (`.env`) and verifies required workspace tools
# (`node`, `pnpm`, `python`, `uv`) across the
# Exygen monorepo or for specific apps under `apps/`.
#
# Current File: win/set-env.ps1
# Commands: [all|root|agent|api|web ...] [--force|-f] [--sync] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
. (Join-Path $ScriptDir "logs.ps1")

$ErrorActionPreference = "Stop"

function Show-Usage {
    info "Usage: .\scripts\win\set-env.ps1 [targets...] [options]"
    info "Targets:"
    info "  all                 Configure .env files for root, agent, api, and web (default)"
    info "  root                Configure root .env file"
    info "  agent               Configure apps/agent/.env file"
    info "  api                 Configure apps/api/.env file"
    info "  web                 Configure apps/web/.env file"
    info "Options:"
    info "  --force, -f         Overwrite existing .env files"
    info "  --sync              Run 'uv sync --all-packages' and 'pnpm install' after configuring env"
    info "  --dry-run           Log actions without writing files or running commands"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  .\scripts\win\set-env.ps1"
    info "  .\scripts\win\set-env.ps1 api web"
    info "  .\scripts\win\set-env.ps1 all --force --sync"
}

function Test-RequiredTools {
    $missing = 0
    foreach ($tool in @("node", "pnpm", "uv")) {
        $cmd = Get-Command $tool -ErrorAction SilentlyContinue
        if ($cmd) {
            info "Detected required tool: $tool ($($cmd.Source))"
        } else {
            error "Missing required tool: $tool"
            $missing++
        }
    }

    $pyCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pyCmd) {
        $pyCmd = Get-Command "python3" -ErrorAction SilentlyContinue
    }
    if ($pyCmd) {
        info "Detected required tool: python ($($pyCmd.Source))"
    } else {
        error "Missing required tool: python"
        $missing++
    }

    if ($missing -gt 0) {
        error "Please install missing tools before continuing."
        exit 1
    }
}

function Write-EnvFile {
    param(
        [string]$TargetPath,
        [string]$Content,
        [bool]$ForceWrite,
        [bool]$IsDryRun
    )

    if ((Test-Path $TargetPath) -and (-not $ForceWrite)) {
        info "Skipping existing env file (use --force to overwrite): $TargetPath"
        return
    }

    if ($IsDryRun) {
        info "[dry-run] Would write env file: $TargetPath"
        return
    }

    Set-Content -LiteralPath $TargetPath -Value $Content -Encoding UTF8
    success "Wrote environment file: $TargetPath"
}

function Set-TargetEnvironment {
    param(
        [string]$Target,
        [bool]$ForceWrite,
        [bool]$IsDryRun
    )

    switch ($Target) {
        "root" {
            $examplePath = Join-Path $RootDir ".env.example"
            if (Test-Path $examplePath) {
                $content = Get-Content -LiteralPath $examplePath -Raw
            } else {
                $content = @"
# Exygen Root Environment
EXYGEN_ENV=development
API_HOST=127.0.0.1
API_PORT=8000
WEB_PORT=3000
VITE_API_URL=http://localhost:8000
EXYGEN_LLM_PROVIDER=deterministic_fallback
"@
            }
            Write-EnvFile -TargetPath (Join-Path $RootDir ".env") -Content $content.TrimEnd() -ForceWrite $ForceWrite -IsDryRun $IsDryRun
        }
        "agent" {
            $content = @"
# Exygen Agent Environment
EXYGEN_LLM_PROVIDER=deterministic_fallback
EXYGEN_DEFAULT_COURSE=COMP-251
"@
            Write-EnvFile -TargetPath (Join-Path $RootDir "apps\agent\.env") -Content $content.TrimEnd() -ForceWrite $ForceWrite -IsDryRun $IsDryRun
        }
        "api" {
            $content = @"
# Exygen API Environment
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
EXYGEN_LLM_PROVIDER=deterministic_fallback
"@
            Write-EnvFile -TargetPath (Join-Path $RootDir "apps\api\.env") -Content $content.TrimEnd() -ForceWrite $ForceWrite -IsDryRun $IsDryRun
        }
        "web" {
            $content = @"
# Exygen Web Environment
VITE_API_URL=http://localhost:8000
"@
            Write-EnvFile -TargetPath (Join-Path $RootDir "apps\web\.env") -Content $content.TrimEnd() -ForceWrite $ForceWrite -IsDryRun $IsDryRun
        }
    }
}

$Force = $false
$SyncDeps = $false
$DryRun = $false
$Requested = New-Object System.Collections.Generic.List[string]

foreach ($arg in $args) {
    switch ($arg) {
        { $_ -in @("--help", "-h", "/?") } {
            Show-Usage
            exit 0
        }
        { $_ -in @("--force", "-f") } { $Force = $true }
        "--sync" { $SyncDeps = $true }
        "--dry-run" { $DryRun = $true }
        "--all" { $Requested.Add("all") }
        { $_.StartsWith("-") } {
            error "Unknown option: $arg"
            Show-Usage
            exit 1
        }
        default {
            foreach ($part in ($arg -split ",")) {
                $norm = $part -replace "^apps[\\/]", "" -replace "[\\/]$", ""
                if ($norm -in @("all", "root", "agent", "api", "web")) {
                    $Requested.Add($norm)
                } else {
                    error "Unknown target: '$part'. Expected: all, root, agent, api, web."
                    exit 1
                }
            }
        }
    }
}

Test-RequiredTools

if ($Requested.Count -eq 0 -or $Requested.Contains("all")) {
    $Targets = @("root", "agent", "api", "web")
} else {
    $Targets = $Requested | Select-Object -Unique
}

foreach ($target in $Targets) {
    Set-TargetEnvironment -Target $target -ForceWrite $Force -IsDryRun $DryRun
}

if ($SyncDeps) {
    Push-Location $RootDir
    try {
        if ($DryRun) {
            info "[dry-run] Would run: uv sync --all-packages && pnpm install"
        } else {
            info "Syncing Python workspace dependencies with uv..."
            & uv sync --all-packages
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            info "Installing Node workspace dependencies with pnpm..."
            & pnpm install
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            success "Workspace dependencies synchronized."
        }
    } finally {
        Pop-Location
    }
}

success "Environment setup complete."
