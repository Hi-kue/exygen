# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script is responsible for logging messages
# with different severity levels (info, warn, error,
# success, debug) to the console with appropriate
# colors and timestamps in Windows PowerShell.
#
# Current File: win/logs.ps1
# Commands: info, warn, error, success, debug
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

$ErrorActionPreference = "Stop"

function Get-LogTimestamp {
    return (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
}

function info {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    $ts = Get-LogTimestamp
    Write-Host "[INFO]" -ForegroundColor Blue -NoNewline
    Write-Host " [$ts] $Message"
}

function warn {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    $ts = Get-LogTimestamp
    Write-Host "[WARN]" -ForegroundColor Yellow -NoNewline
    Write-Host " [$ts] $Message" -ForegroundColor Yellow
}

function error {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    $ts = Get-LogTimestamp
    Write-Host "[ERROR]" -ForegroundColor Red -NoNewline
    Write-Host " [$ts] $Message" -ForegroundColor Red
}

function success {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    $ts = Get-LogTimestamp
    Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline
    Write-Host " [$ts] $Message" -ForegroundColor Green
}

function debug {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Message)
    $ts = Get-LogTimestamp
    Write-Host "[DEBUG]" -ForegroundColor Magenta -NoNewline
    Write-Host " [$ts] $Message" -ForegroundColor Magenta
}
