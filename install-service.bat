@echo off
setlocal

REM Hypernet Swarm — Windows Service Installer
REM Run as Administrator (right-click CMD, Run as Administrator)

set "SVCNAME=HypernetSwarm"
set "WORKDIR=%~dp0"
REM Remove trailing backslash
if "%WORKDIR:~-1%"=="\" set "WORKDIR=%WORKDIR:~0,-1%"
set "LOGDIR=%WORKDIR%\data\logs"

echo ============================================================
echo   Hypernet Swarm — Service Installer
echo ============================================================
echo.

REM ── Find Python ────────────────────────────────────────────

set "PYTHON="
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%i in ('where python') do (
        if not defined PYTHON set "PYTHON=%%i"
    )
)
if not defined PYTHON (
    echo ERROR: Python not found. Run install.bat first.
    pause
    exit /b 1
)
echo   Python: %PYTHON%

REM ── Find NSSM ─────────────────────────────────────────────

set "NSSM="
where nssm >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%i in ('where nssm') do (
        if not defined NSSM set "NSSM=%%i"
    )
)
if not defined NSSM (
    if exist "C:\Users\spamm\AppData\Local\Microsoft\WinGet\Links\nssm.exe" (
        set "NSSM=C:\Users\spamm\AppData\Local\Microsoft\WinGet\Links\nssm.exe"
    )
)
if not defined NSSM (
    echo.
    echo   NSSM (Non-Sucking Service Manager) is required.
    echo   Install with: winget install nssm
    echo   Or download from: https://nssm.cc/download
    echo.
    set /p INSTALL_NSSM="   Install NSSM via winget now? (Y/N): "
    if /i "%INSTALL_NSSM%"=="Y" (
        winget install nssm
        where nssm >nul 2>&1
        if errorlevel 1 (
            echo   NSSM install failed. Install manually and try again.
            pause
            exit /b 1
        )
        for /f "delims=" %%i in ('where nssm') do set "NSSM=%%i"
    ) else (
        pause
        exit /b 1
    )
)
echo   NSSM:   %NSSM%

REM ── Detect archive root ────────────────────────────────────

set "ARCHIVE="
if exist "C:\Hypernet\Hypernet Structure" (
    set "ARCHIVE=C:\Hypernet\Hypernet Structure"
)
if not defined ARCHIVE (
    if exist "%USERPROFILE%\Hypernet\Hypernet Structure" (
        set "ARCHIVE=%USERPROFILE%\Hypernet\Hypernet Structure"
    )
)

set "ARCHIVE_ARG="
if defined ARCHIVE (
    echo   Archive: %ARCHIVE%
    set "ARCHIVE_ARG= --archive \"%ARCHIVE%\""
)

echo   WorkDir: %WORKDIR%
echo.

REM ── Create log directory ───────────────────────────────────

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM ── Remove old service ─────────────────────────────────────

echo Removing old service if any...
sc stop %SVCNAME% >nul 2>&1
sc delete %SVCNAME% >nul 2>&1
timeout /t 3 /nobreak >nul

REM ── Install via NSSM ───────────────────────────────────────

echo Installing service...
"%NSSM%" install %SVCNAME% "%PYTHON%"
if errorlevel 1 (
    echo ERROR: nssm install failed. Are you running as Administrator?
    pause
    exit /b 1
)

echo Configuring service...
if defined ARCHIVE (
    "%NSSM%" set %SVCNAME% AppParameters "-m hypernet_swarm --archive \"%ARCHIVE%\""
) else (
    "%NSSM%" set %SVCNAME% AppParameters "-m hypernet_swarm"
)
"%NSSM%" set %SVCNAME% AppDirectory "%WORKDIR%"
"%NSSM%" set %SVCNAME% AppStdout "%LOGDIR%\service-stdout.log"
"%NSSM%" set %SVCNAME% AppStderr "%LOGDIR%\service-stderr.log"
"%NSSM%" set %SVCNAME% AppStdoutCreationDisposition 4
"%NSSM%" set %SVCNAME% AppStderrCreationDisposition 4
"%NSSM%" set %SVCNAME% Start SERVICE_AUTO_START
"%NSSM%" set %SVCNAME% DisplayName "Hypernet Swarm"
"%NSSM%" set %SVCNAME% Description "Hypernet AI Swarm Orchestrator"

echo Starting service...
"%NSSM%" start %SVCNAME%

echo.
echo Waiting 10 seconds for startup...
timeout /t 10 /nobreak >nul

"%NSSM%" status %SVCNAME%
echo.
echo ============================================================
echo   Service installed and started!
echo   Dashboard: http://localhost:8000/swarm/dashboard
echo   Logs:      %LOGDIR%
echo.
echo   Manage:
echo     nssm status %SVCNAME%
echo     nssm restart %SVCNAME%
echo     nssm stop %SVCNAME%
echo ============================================================
echo.
pause
endlocal
