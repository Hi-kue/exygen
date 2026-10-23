@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script runs the Exygen monorepo packages under
REM `apps\` (`agent`, `api`, `web`) either separately,
REM in custom combinations (e.g., `api web`), or all at
REM once in sequential order (`agent` -> `api` -> `web`)
REM or parallel mode.
REM
REM Current File: win/run.cmd
REM Commands: [all|agent|api|web ...] [--sequential|-s] [--parallel|-p] [--strict-sequential] [--dry-run] [--help|-h]
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "LOGS=%SCRIPT_DIR%logs.cmd"
for %%I in ("%SCRIPT_DIR%..\..") do set "ROOT_DIR=%%~fI"

set "MODE=sequential"
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
if /i "!ARG!"=="--strict-sequential" ( set "MODE=strict-sequential" & shift & goto parse_args )
if /i "!ARG!"=="--parallel" ( set "MODE=parallel" & shift & goto parse_args )
if /i "!ARG!"=="-p" ( set "MODE=parallel" & shift & goto parse_args )
if /i "!ARG!"=="--together" ( set "MODE=parallel" & shift & goto parse_args )
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
call "%LOGS%" info "Selected applications (!MODE!):!TARGETS_LIST!"

if /i "!MODE!"=="parallel" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would run in parallel: pnpm nx run-many -t dev --projects=!TARGETS_CSV!"
        popd
        exit /b 0
    )
    call "%LOGS%" info "Starting applications in parallel via Nx: !TARGETS_CSV!"
    call pnpm nx run-many -t dev --projects=!TARGETS_CSV!
    popd
    exit /b %ERRORLEVEL%
)

if "!DO_AGENT!"=="1" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would run 'agent': pnpm nx run agent:dev"
    ) else (
        call "%LOGS%" info "Running 'agent' pipeline (apps\agent)..."
        call pnpm nx run agent:dev
        if errorlevel 1 ( popd & exit /b 1 )
        call "%LOGS%" success "Completed 'agent' pipeline."
    )
)

if "!DO_API!"=="1" if "!DO_WEB!"=="1" if /i "!MODE!"=="sequential" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would start service 'api': pnpm nx run api:dev"
        call "%LOGS%" info "[dry-run] Would start service 'web': pnpm nx run web:dev"
        popd
        exit /b 0
    )
    where powershell >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        popd
        powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run.ps1" api web
        exit /b %ERRORLEVEL%
    )
    call "%LOGS%" info "Starting 'api' and 'web' via Nx..."
    call pnpm nx run-many -t dev --projects=api,web
    popd
    exit /b %ERRORLEVEL%
)

if "!DO_API!"=="1" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would run 'api': pnpm nx run api:dev"
    ) else (
        call "%LOGS%" info "Starting 'api' (apps\api)..."
        call pnpm nx run api:dev
        if errorlevel 1 ( popd & exit /b 1 )
    )
)

if "!DO_WEB!"=="1" (
    if "!DRY_RUN!"=="1" (
        call "%LOGS%" info "[dry-run] Would run 'web': pnpm nx run web:dev"
    ) else (
        call "%LOGS%" info "Starting 'web' (apps\web)..."
        call pnpm nx run web:dev
        if errorlevel 1 ( popd & exit /b 1 )
    )
)

popd
exit /b 0

:show_usage
call "%LOGS%" info "Usage: scripts\win\run.cmd [all|agent|api|web ...] [--sequential|-s] [--parallel|-p] [--strict-sequential] [--dry-run] [--help|-h]"
call "%LOGS%" info "Targets: all (default: agent -> api -> web), agent, api, web"
call "%LOGS%" info "Options: --sequential (-s), --strict-sequential, --parallel (-p), --dry-run, --help (-h)"
exit /b 0

:show_usage_err
call "%LOGS%" info "Usage: scripts\win\run.cmd [all|agent|api|web ...] [--sequential|-s] [--parallel|-p] [--strict-sequential] [--dry-run] [--help|-h]"
exit /b 1
