@echo off
REM NutriVault One-Stop Double-Click Launcher for Windows
cd /d "%~dp0"

echo ===========================================================
echo   NutriVault - Local-First Personal and Family Nutrition
echo ===========================================================
echo   Your web browser will open automatically in a moment...
echo   (Keep this window open while using NutriVault.)
echo ===========================================================

REM 1. If Docker Desktop is running, start the turnkey Docker stack
where docker >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    docker info >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo -^> Docker Desktop detected. Starting NutriVault + Camera AI...
        start "" "http://localhost:8080"
        docker compose up
        goto :eof
    )
)

REM 2. Otherwise use portable uv (installing automatically if not yet present)
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo -^> Installing lightweight Python environment manager (one-time setup)...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)

echo -^> Starting NutriVault on http://localhost:8080 ...
uv run python -m src.api --open-browser
pause
