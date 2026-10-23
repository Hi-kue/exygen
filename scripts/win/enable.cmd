@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script unblocks all Windows scripts located
REM in `scripts\win\` so they can be executed without
REM security prompts on Windows.
REM
REM Current File: win/enable.cmd
REM Commands: N/A
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOGS=%SCRIPT_DIR%logs.cmd"

call "%LOGS%" info "Enabling and unblocking scripts in scripts\win\..."

where powershell >nul 2>nul
if %ERRORLEVEL% equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%enable.ps1"
    exit /b %ERRORLEVEL%
)

call "%LOGS%" success "All .cmd scripts in scripts\win\ are ready to execute."
exit /b 0
