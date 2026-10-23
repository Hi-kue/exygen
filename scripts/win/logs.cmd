@echo off
REM README
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
REM This script is responsible for logging messages
REM with different severity levels (info, warn, error,
REM success, debug) to the console with appropriate
REM colors and timestamps in Windows Command Prompt.
REM
REM Current File: win/logs.cmd
REM Commands: info, warn, error, success, debug
REM *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

setlocal EnableDelayedExpansion

set "LEVEL=%~1"
set "MSG=%~2"

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "TODAY=%date%"
set "NOW=%time:~0,8%"
set "NOW=!NOW: =0!"
set "STAMP=!TODAY! !NOW!"

for /f %%e in ('echo prompt $E^| cmd') do set "ESC=%%e"

set "C_RESET=!ESC![0m"
set "C_RED=!ESC![31m"
set "C_GREEN=!ESC![32m"
set "C_YELLOW=!ESC![33m"
set "C_BLUE=!ESC![34m"
set "C_MAGENTA=!ESC![35m"

if /i "!LEVEL!"=="info" (
    echo !C_BLUE![INFO]!C_RESET! [!STAMP!] !MSG!
    exit /b 0
)
if /i "!LEVEL!"=="warn" (
    echo !C_YELLOW![WARN]!C_RESET! [!STAMP!] !C_YELLOW!!MSG!!C_RESET! >&2
    exit /b 0
)
if /i "!LEVEL!"=="error" (
    echo !C_RED![ERROR]!C_RESET! [!STAMP!] !C_RED!!MSG!!C_RESET! >&2
    exit /b 0
)
if /i "!LEVEL!"=="success" (
    echo !C_GREEN![SUCCESS]!C_RESET! [!STAMP!] !C_GREEN!!MSG!!C_RESET!
    exit /b 0
)
if /i "!LEVEL!"=="debug" (
    echo !C_MAGENTA![DEBUG]!C_RESET! [!STAMP!] !C_MAGENTA!!MSG!!C_RESET!
    exit /b 0
)

echo !C_BLUE![INFO]!C_RESET! [!STAMP!] %*
exit /b 0
