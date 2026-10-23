@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script builds the Exygen monorepo packages
REM under `apps\` (`agent`, `api`, `web`) either
REM separately, in custom combinations, or all at once
REM in sequential order (`agent` -> `api` -> `web`).
REM
REM Current File: win/build.cmd
REM Commands: [all|agent|api|web ...] [--parallel|-p] [--no-cache] [--dry-run] [--help|-h]
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOGS=%SCRIPT_DIR%logs.cmd"
for %%I in ("%SCRIPT_DIR%..\..") do set "ROOT_DIR=%%~fI"

set "MODE=sequential"
set "NO_CACHE=0"
set "DRY_RUN=0"
set "DO_ALL=0"
set "DO_AGENT=0"
set "DO_API=0"
set "DO_WEB=0"
set "HAS_TARGET=0"

:parse_args
if "%~1"=="" goto after_parse
set "ARG=%~1"

if /i "!ARG!"=="--help" goto show_usage
if /i "!ARG!"=="-h" goto show_usage
if /i "!ARG!"=="/?" goto show_usage
if /i "!ARG!"=="--sequential" ( set "MODE=sequential" & shift & goto parse_args )
if /i "!ARG!"=="-s" ( set "MODE=sequential" & shift & goto parse_args )
if /i "!ARG!"=="--parallel" ( set "MODE=parallel" & shift & goto parse_args )
if /i "!ARG!"=="-p" ( set "MODE=parallel" & shift & goto parse_args )
if /i "!ARG!"=="--no-cache" ( set "NO_CACHE=1" & shift & goto parse_args )
if /i "!ARG!"=="--skip-nx-cache" ( set "NO_CACHE=1" & shift & goto parse_args )
if /i "!ARG!"=="--dry-run" ( set "DRY_RUN=1" & shift & goto parse_args )
if /i "!ARG!"=="all" ( set "DO_ALL=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="--all" ( set "DO_ALL=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="agent" ( set "DO_AGENT=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="--agent" ( set "DO_AGENT=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps/agent" ( set "DO_AGENT=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps\agent" ( set "DO_AGENT=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="api" ( set "DO_API=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="--api" ( set "DO_API=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps/api" ( set "DO_API=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps\api" ( set "DO_API=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="web" ( set "DO_WEB=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="--web" ( set "DO_WEB=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps/web" ( set "DO_WEB=1" & set "HAS_TARGET=1" & shift & goto parse_args )
if /i "!ARG!"=="apps\web" ( set "DO_WEB=1" & set "HAS_TARGET=1" & shift & goto parse_args )

call "%LOGS%" error "Unknown target or option: !ARG!"
goto show_usage_err

:after_parse
if "!HAS_TARGET!"=="0" set "DO_ALL=1"
if "!DO_ALL!"=="1" (
    set "DO_AGENT=1"
    set "DO_API=1"
    set "DO_WEB=1"
)

set "NX_FLAGS="
if "!NO_CACHE!"=="1" set "NX_FLAGS=--skip-nx-cache"

set "TARGETS_LIST="
set "TARGETS_CSV="
if "!DO_AGENT!"=="1" (
    set "TARGETS_LIST=!TARGETS_LIST! agent"
    set "TARGETS_CSV=agent"
)
if "!DO_API!"=="1" (
    set "TARGETS_LIST=!TARGETS_LIST! api"
    if defined TARGETS_CSV ( set "TARGETS_CSV=!TARGETS_CSV!,api" ) else ( set "TARGETS_CSV=api" )
)
if "!DO_WEB!"=="1" (
    set "TARGETS_LIST=!TARGETS_LIST! web"
    if defined TARGETS_CSV ( set "TARGETS_CSV=!TARGETS_CSV!,web" ) else ( set "TARGETS_CSV=web" )
)

pushd "%ROOT_DIR%"
call "%LOGS%" info "Selected build targets (!MODE!):!TARGETS_LIST!"

if /i "!MODE!"=="parallel" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would run: pnpm nx run-many -t build --projects=!TARGETS_CSV! !NX_FLAGS!"
        popd
        exit /b 0
    )
    call "%LOGS%" info "Running parallel build for: !TARGETS_CSV!"
    call pnpm nx run-many -t build --projects=!TARGETS_CSV! !NX_FLAGS!
    if errorlevel 1 ( popd & exit /b 1 )
    call "%LOGS%" success "Completed parallel build for:!TARGETS_LIST!"
    popd
    exit /b 0
)

for %%A in (!TARGETS_LIST!) do (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would build '%%A': pnpm nx run %%A:build !NX_FLAGS!"
    ) else (
        call "%LOGS%" info "Building '%%A' (apps\%%A)..."
        call pnpm nx run %%A:build !NX_FLAGS!
        if errorlevel 1 (
            call "%LOGS%" error "Failed to build '%%A'."
            popd
            exit /b 1
        )
        call "%LOGS%" success "Built '%%A' successfully."
    )
)

if "!DRY_RUN!"=="1" (
    call "%LOGS%" info "Dry-run complete. No packages were built."
) else (
    call "%LOGS%" success "All requested packages built (!TARGETS_LIST! )."
)
popd
exit /b 0

:show_usage
call "%LOGS%" info "Usage: scripts\win\build.cmd [all|agent|api|web ...] [--parallel|-p] [--no-cache] [--dry-run] [--help|-h]"
call "%LOGS%" info "Targets: all (default: agent -> api -> web), agent, api, web"
call "%LOGS%" info "Options: --sequential (-s), --parallel (-p), --no-cache, --dry-run, --help (-h)"
exit /b 0

:show_usage_err
call "%LOGS%" info "Usage: scripts\win\build.cmd [all|agent|api|web ...] [--parallel|-p] [--no-cache] [--dry-run] [--help|-h]"
exit /b 1
