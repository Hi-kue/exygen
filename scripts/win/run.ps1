# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script runs the Exygen monorepo packages under
# `apps/` (`agent`, `api`, `web`) either separately,
# in custom combinations (e.g., `api web`), or all at
# once in sequential order (`agent` -> `api` -> `web`)
# or parallel mode on Windows PowerShell.
#
# Current File: win/run.ps1
# Commands: [all|agent|api|web ...] [--sequential|-s] [--parallel|-p] [--strict-sequential] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
. (Join-Path $ScriptDir "logs.ps1")

$ErrorActionPreference = "Stop"
$ValidApps = @("agent", "api", "web")

function Show-Usage {
    info "Usage: .\scripts\win\run.ps1 [targets...] [options]"
    info "Targets:"
    info "  all                   Run all applications in sequential order: agent -> api -> web (default)"
    info "  agent                 Run apps/agent (Python multi-agent pipeline CLI)"
    info "  api                   Run apps/api (FastAPI server on port 8000)"
    info "  web                   Run apps/web (React + TanStack dev server on port 3000)"
    info "Options:"
    info "  --sequential, -s      Start targets in sequential order (default)"
    info "  --strict-sequential   Run each target in foreground strictly one after another"
    info "  --parallel, -p        Run selected targets concurrently via Nx run-many"
    info "  --dry-run             Log the commands that would be executed without running them"
    info "  --help, -h            Show this help message"
    info "Examples:"
    info "  .\scripts\win\run.ps1"
    info "  .\scripts\win\run.ps1 agent"
    info "  .\scripts\win\run.ps1 api"
    info "  .\scripts\win\run.ps1 web"
    info "  .\scripts\win\run.ps1 api web"
    info "  .\scripts\win\run.ps1 all --parallel"
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
        "--strict-sequential" {
            $Mode = "strict-sequential"
        }
        { $_ -in @("--parallel", "-p", "--together") } {
            $Mode = "parallel"
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
                    error "Unknown application target: '$part'. Expected one of: all, agent, api, web."
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

Push-Location $RootDir
try {
    info "Selected applications ($Mode): $($Targets -join ' ')"

    if ($Targets.Count -eq 1) {
        $app = $Targets[0]
        if ($DryRun) {
            info "[dry-run] Would run '$app': pnpm nx run ${app}:dev"
            exit 0
        }
        info "Running '$app' (apps/$app)..."
        & pnpm nx run "${app}:dev"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        success "Finished running '$app'."
        exit 0
    }

    if ($Mode -eq "parallel") {
        $projectsCsv = $Targets -join ","
        if ($DryRun) {
            info "[dry-run] Would run in parallel: pnpm nx run-many -t dev --projects=$projectsCsv"
            exit 0
        }
        info "Starting applications in parallel via Nx: $projectsCsv"
        & pnpm nx run-many -t dev "--projects=$projectsCsv"
        exit $LASTEXITCODE
    }

    if ($Mode -eq "strict-sequential") {
        $step = 1
        $total = $Targets.Count
        foreach ($app in $Targets) {
            if ($DryRun) {
                info "[dry-run] ($step/$total) Would run '$app': pnpm nx run ${app}:dev"
            } else {
                info "($step/$total) Running '$app' (apps/$app)..."
                & pnpm nx run "${app}:dev"
                if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                success "($step/$total) Finished '$app'."
            }
            $step++
        }
        exit 0
    }

    $step = 1
    $total = $Targets.Count
    $services = New-Object System.Collections.Generic.List[string]

    foreach ($app in $Targets) {
        if ($app -eq "agent") {
            if ($DryRun) {
                info "[dry-run] ($step/$total) Would run 'agent': pnpm nx run agent:dev"
            } else {
                info "($step/$total) Running 'agent' pipeline (apps/agent)..."
                & pnpm nx run "agent:dev"
                if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                success "($step/$total) Completed 'agent' pipeline."
            }
            $step++
        } else {
            $services.Add($app)
        }
    }

    if ($services.Count -eq 0) {
        exit 0
    }

    if ($services.Count -eq 1) {
        $svc = $services[0]
        if ($DryRun) {
            info "[dry-run] ($step/$total) Would run '$svc': pnpm nx run ${svc}:dev"
            exit 0
        }
        info "($step/$total) Starting '$svc' (apps/$svc)..."
        & pnpm nx run "${svc}:dev"
        exit $LASTEXITCODE
    }

    if ($DryRun) {
        foreach ($svc in $services) {
            info "[dry-run] ($step/$total) Would start service '$svc': pnpm nx run ${svc}:dev"
            $step++
        }
        exit 0
    }

    $processes = New-Object System.Collections.Generic.List[System.Diagnostics.Process]
    try {
        foreach ($svc in $services) {
            info "($step/$total) Starting service '$svc' (apps/$svc)..."
            $proc = Start-Process -FilePath "pnpm" -ArgumentList @("nx", "run", "${svc}:dev") -WorkingDirectory $RootDir -NoNewWindow -PassThru
            $processes.Add($proc)
            Start-Sleep -Seconds 1
            $step++
        }
        success "All requested services started in sequential order ($($services -join ' ')). Press Ctrl+C to stop."
        Wait-Process -Id ($processes | ForEach-Object { $_.Id })
    } finally {
        foreach ($proc in $processes) {
            if (-not $proc.HasExited) {
                info "Stopping service process $($proc.Id)..."
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
} finally {
    Pop-Location
}
