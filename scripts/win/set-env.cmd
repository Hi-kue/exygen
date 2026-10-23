@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script initializes local environment files
REM (`.env`) and verifies required workspace tools
REM (`node`, `pnpm`, `python`, `uv`) across the
REM Exygen monorepo or for specific apps under `apps\`.
REM
REM Current File: win/set-env.cmd
REM Commands: [all|root|agent|api|web ...] [--force|-f] [--sync] [--dry-run] [--help|-h]
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOGS=%SCRIPT_DIR%logs.cmd"

if /i "%~1"=="--help" goto show_usage
if /i "%~1"=="-h" goto show_usage
if /i "%~1"=="/?" goto show_usage

where powershell >nul 2>nul
if %ERRORLEVEL% equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%set-env.ps1" %*
    exit /b %ERRORLEVEL%
)

call "%LOGS%" error "PowerShell is required to run set-env.cmd on Windows."
exit /b 1

:show_usage
call "%LOGS%" info "Usage: scripts\win\set-env.cmd [all|root|agent|api|web ...] [--force|-f] [--sync] [--dry-run] [--help|-h]"
call "%LOGS%" info "Targets: all (default), root, agent, api, web"
call "%LOGS%" info "Options: --force (-f), --sync, --dry-run, --help (-h)"
exit /b 0
