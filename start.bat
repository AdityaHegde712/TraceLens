@echo off
setlocal enabledelayedexpansion

title TraceLens Dashboard Launcher
cd /d "%~dp0"

chcp 65001 >nul

:: Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ======================================================================
    echo Creating virtual environment .venv...
    echo ======================================================================
    where uv >nul 2>nul
    if %errorlevel% equ 0 (
        uv venv --python 3.13 .venv
        if %errorlevel% neq 0 (
            uv venv .venv
        )
        call .venv\Scripts\activate.bat
        uv pip install -e ".[dev]"
    ) else (
        python -m venv .venv
        call .venv\Scripts\activate.bat
        pip install -e ".[dev]"
    )
) else (
    call .venv\Scripts\activate.bat
)

set PORT=8000
set HOST=127.0.0.1
set URL=http://%HOST%:%PORT%

echo ======================================================================
echo  TraceLens: Evidence-Grounded Incident Triage Assistant for RAG APIs
echo  Web UI Dashboard: %URL%
echo ======================================================================

:: Open default browser after brief delay
start /b "" cmd /c "timeout /t 1 /nobreak >nul & start %URL%"

:: Launch UI server
tracelens ui --host %HOST% --port %PORT%

pause
