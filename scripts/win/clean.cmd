@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script removes build and cache artifacts from
REM the entire Exygen codebase or from specific app
REM folders under `apps\` (`agent`, `api`, `web`).
REM
REM Current File: win/clean.cmd
REM Commands: [all|agent|api|web|path ...] [--dry-run] [--yes|-y] [--help|-h]
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOGS=%SCRIPT_DIR%logs.cmd"

if /i "%~1"=="--help" goto show_usage
if /i "%~1"=="-h" goto show_usage
if /i "%~1"=="/?" goto show_usage

where powershell >nul 2>nul
if %ERRORLEVEL% equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%clean.ps1" %*
    exit /b %ERRORLEVEL%
)

call "%LOGS%" error "PowerShell is required to run clean.cmd on Windows."
exit /b 1

:show_usage
call "%LOGS%" info "Usage: scripts\win\clean.cmd [all|agent|api|web|path ...] [--dry-run] [--yes|-y] [--help|-h]"
call "%LOGS%" info "Targets: all (default), agent, api, web, or a custom directory path"
call "%LOGS%" info "Options: --dry-run, --yes (-y), --help (-h)"
exit /b 0
