# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script unblocks all Windows PowerShell (.ps1)
# and Batch (.cmd) scripts located in `scripts/win/`
# so they can be executed without Zone.Identifier
# security prompts on Windows.
#
# Current File: win/enable.ps1
# Commands: N/A
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "logs.ps1")

$ErrorActionPreference = "Stop"

try {
    info "Unblocking all .ps1 and .cmd scripts in scripts/win/..."
    Get-ChildItem -Path $ScriptDir -Include "*.ps1", "*.cmd" -File | ForEach-Object {
        Unblock-File -Path $_.FullName -ErrorAction SilentlyContinue
    }
    success "All scripts in scripts/win/ have been unblocked and enabled for execution."
} catch {
    error "Failed to unblock scripts in scripts/win/: $_"
    exit 1
}
