@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Hypernet Swarm — Installer
echo ============================================================
echo.
echo   This script will:
echo     1. Check for Python 3.10+ (offer to install if missing)
echo     2. Show required packages and install with your permission
echo     3. Run the interactive setup wizard (API keys, config)
echo     4. Optionally install as a Windows service
echo.

REM ── Step 1: Check Python ──────────────────────────────────

echo [1/4] Checking Python...
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo   Python is NOT installed or not in PATH.
    echo.
    echo   The Hypernet Swarm requires Python 3.10 or newer.
    echo   The installer can download Python 3.12.4 for you.
    echo.
    set /p "INSTALL_PYTHON=  Download and install Python 3.12.4 now? (Y/N): "
    if /i "!INSTALL_PYTHON!"=="Y" (
        echo.
        echo   Downloading Python 3.12.4 installer...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python-installer.exe'"
        if errorlevel 1 (
            echo   ERROR: Download failed. Install manually from:
            echo     https://www.python.org/downloads/
            echo   Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
        echo   Launching Python installer...
        echo.
        echo   *** IMPORTANT: Check "Add Python to PATH" at the bottom! ***
        echo.
        start /wait "" "%TEMP%\python-installer.exe"
        echo.
        echo   Python installed. Verifying...
        python --version >nul 2>&1
        if errorlevel 1 (
            echo   Python is still not on PATH. Please close this window,
            echo   reopen a new command prompt, and run install.bat again.
            pause
            exit /b 0
        )
    ) else (
        echo.
        echo   Python is required. Install from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%V in ('python --version 2^>^&1') do set "PYVER=%%V"
echo   Found: %PYVER%
echo.

REM ── Step 2: Show and install dependencies ──────────────────

echo [2/4] Package dependencies
echo.
echo   The following Python packages are needed:
echo.
echo   Required:
echo     anthropic          - Claude API client (Anthropic)
echo     openai             - GPT API client (also used for Gemini, Groq, etc.)
echo     httpx              - HTTP client for API calls
echo.
echo   Recommended (for the web dashboard):
echo     fastapi            - Web framework for the dashboard and REST API
echo     uvicorn            - Web server to run FastAPI
echo.
echo   Optional:
echo     pyyaml             - YAML config file support
echo     pystray            - System tray icon (Windows)
echo     Pillow             - Image support for tray icon
echo     pytest             - Test runner (development)
echo.

set /p "INSTALL_DEPS=  Install all packages now? (Y/N): "
if /i "!INSTALL_DEPS!"=="Y" (
    echo.
    echo   Checking pip...
    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo   Installing pip...
        python -m ensurepip --upgrade >nul 2>&1
    )
    echo   Installing packages (this may take a minute)...
    echo.
    python -m pip install -e ".[all]" --quiet 2>nul
    if errorlevel 1 (
        echo   Some optional packages failed. Installing core only...
        python -m pip install -e . --quiet
    )
    echo.
    echo   Verifying installation...
    python bootstrap.py
    echo.
) else (
    echo.
    echo   Skipped. You can install manually later with:
    echo     pip install -e ".[all]"
    echo.
)

REM ── Step 3: Run setup wizard ──────────────────────────────

echo [3/4] Setup wizard
echo.
echo   The setup wizard will help you configure API keys, budget,
echo   and other settings. You can re-run it anytime with:
echo     python -m hypernet_swarm setup
echo.

set /p "RUN_SETUP=  Run setup wizard now? (Y/N): "
if /i "!RUN_SETUP!"=="Y" (
    echo.
    python -m hypernet_swarm setup
    echo.
) else (
    echo.
    echo   Skipped. Run later with: python -m hypernet_swarm setup
    echo.
)

REM ── Step 4: Offer service install ──────────────────────────

echo ============================================================
echo   Installation complete!
echo ============================================================
echo.
echo   To start the swarm manually:
echo     python -m hypernet_swarm
echo.
echo   Dashboard (after starting):
echo     http://localhost:8000/swarm/dashboard
echo.
echo   Re-run setup anytime:
echo     python -m hypernet_swarm setup
echo.

set /p "INSTALL_SVC=  Install as a Windows service (auto-starts on boot)? (Y/N): "
if /i "!INSTALL_SVC!"=="Y" (
    echo.
    echo   Installing service (may require Administrator privileges)...
    call "%~dp0install-service.bat"
) else (
    echo.
    echo   You can install the service later by running:
    echo     install-service.bat  (as Administrator)
)

echo.
pause
endlocal
