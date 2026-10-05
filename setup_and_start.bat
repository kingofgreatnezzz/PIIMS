@echo off
REM ===========================================================================
REM  NIGERIA POLICE FORCE - Oji-River Area Command
REM  Police Intelligence and Information Management System (PIIMS)
REM
REM  setup_and_start.bat
REM  -------------------
REM  One-click Windows launcher.  Double-click this file and the script will:
REM     1. Locate a Python 3 interpreter on this computer
REM     2. Create the virtual environment (venv) if it does not exist
REM     3. Activate the virtual environment
REM     4. Install everything listed in requirements.txt
REM     5. Build and seed the SQLite database (police_ims.db) if it is missing
REM     6. Start the Streamlit application
REM
REM  Optional switches:
REM     setup_and_start.bat --reinstall    force reinstallation of dependencies
REM     setup_and_start.bat --reset-db     rebuild the database from scratch
REM     setup_and_start.bat --port 8502    run the server on another port
REM     setup_and_start.bat --help         show the help screen
REM ===========================================================================

setlocal EnableExtensions EnableDelayedExpansion
title Nigeria Police Force - PIIMS Launcher
cd /d "%~dp0"

set "VENV_DIR=venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "DEPS_MARKER=%VENV_DIR%\.deps_ok"
set "FORCE_INSTALL=0"
set "RESET_DB=0"
set "PORT=8501"

echo.
echo =======================================================================
echo   NIGERIA POLICE FORCE - Oji-River Area Command
echo   Police Intelligence and Information Management System (PIIMS)
echo   Automated setup and launch
echo =======================================================================
echo.

REM ---------------------------------------------------------------------
REM  Command line switches
REM ---------------------------------------------------------------------
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--reinstall" (
    set "FORCE_INSTALL=1"
    shift
    goto parse_args
)
if /i "%~1"=="--reset-db" (
    set "RESET_DB=1"
    shift
    goto parse_args
)
if /i "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--help" goto usage
if /i "%~1"=="-h" goto usage
echo   Unknown option: %~1   (use --help for the list of switches)
echo.
goto fail
:args_done

REM ---------------------------------------------------------------------
REM  STEP 1 - find a Python interpreter
REM ---------------------------------------------------------------------
echo [1/6] Locating Python 3 ...
set "PY_CMD="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3"
if not defined PY_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
    echo.
    echo   ERROR: Python 3 was not found on this computer.
    echo.
    echo   Install Python 3.10 or newer from https://www.python.org/downloads/
    echo   IMPORTANT: tick "Add python.exe to PATH" in the installer.
    echo   Then run this script again.
    goto fail
)
for /f "delims=" %%v in ('%PY_CMD% --version 2^>^&1') do set "PY_VERSION=%%v"
echo        Found %PY_VERSION%   (launcher: %PY_CMD%)

REM ---------------------------------------------------------------------
REM  STEP 2 - create the virtual environment if necessary
REM ---------------------------------------------------------------------
echo [2/6] Checking the virtual environment ...
if exist "%VENV_PY%" (
    echo        Virtual environment already exists in .\%VENV_DIR%
) else (
    echo        Creating virtual environment in .\%VENV_DIR% ...
    %PY_CMD% -m venv "%VENV_DIR%"
    if not exist "%VENV_PY%" (
        echo.
        echo   ERROR: The virtual environment could not be created.
        echo   Check that you have write permission in this folder and try again.
        goto fail
    )
    echo        Virtual environment created.
)

REM ---------------------------------------------------------------------
REM  STEP 3 - activate and make sure pip is available
REM ---------------------------------------------------------------------
echo [3/6] Activating the virtual environment ...
call "%VENV_DIR%\Scripts\activate.bat" >nul 2>&1
if errorlevel 1 (
    echo        Note: the activation script could not be run.
    echo        The application will still use %VENV_DIR%\Scripts\python.exe directly,
    echo        so this is not a problem.
) else (
    echo        Environment activated.
)

"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo        pip is missing - bootstrapping it now ...
    "%VENV_PY%" -m ensurepip --upgrade --default-pip >nul 2>&1
    "%VENV_PY%" -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   ERROR: pip could not be installed inside the virtual environment.
        echo   Delete the "%VENV_DIR%" folder and run this script again.
        goto fail
    )
)
echo        Environment ready.

REM ---------------------------------------------------------------------
REM  STEP 4 - install the dependencies listed in requirements.txt
REM ---------------------------------------------------------------------
echo [4/6] Installing dependencies ...
if "%FORCE_INSTALL%"=="1" goto install_deps
if not exist "%DEPS_MARKER%" goto install_deps
echo        Dependencies were installed previously - skipping.
echo        (use  setup_and_start.bat --reinstall  to force a fresh install)
goto deps_done

:install_deps
echo        Upgrading pip ...
"%VENV_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 echo        Warning: pip upgrade failed - continuing anyway.

echo        Installing Streamlit, Pandas and Pillow (this may take a few minutes) ...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: Dependency installation failed.
    echo   Check your internet connection and try again, or run:
    echo       %VENV_PY% -m pip install -r requirements.txt
    goto fail
)
echo ok> "%DEPS_MARKER%"
echo        Dependencies installed successfully.
:deps_done

REM ---------------------------------------------------------------------
REM  STEP 5 - build / verify the database
REM ---------------------------------------------------------------------
echo [5/6] Preparing the database ...
if "%RESET_DB%"=="1" (
    echo        Rebuilding the database from scratch ...
    "%VENV_PY%" setup_db.py --reset
    if errorlevel 1 goto fail
) else (
    if exist "police_ims.db" (
        echo        Database found: police_ims.db
        "%VENV_PY%" setup_db.py --status
    ) else (
        echo        Database not found - creating tables and sample data ...
        "%VENV_PY%" setup_db.py
        if errorlevel 1 goto fail
    )
)

REM ---------------------------------------------------------------------
REM  STEP 6 - launch the application
REM ---------------------------------------------------------------------
echo [6/6] Starting the PIIMS web application ...
echo.
echo =======================================================================
echo   The application is starting. Your browser will open shortly at
echo       http://localhost:%PORT%
echo.
echo   Sign in with:   admin / admin123      (Administrator)
echo                   viewer / viewer123    (Viewer - read only)
echo.
echo   Keep this window open while you use the system.
echo   Press CTRL+C in this window to stop the server.
echo =======================================================================
echo.

"%VENV_PY%" -m streamlit run app.py --server.port %PORT% --server.headless false --browser.gatherUsageStats false
if errorlevel 1 (
    echo.
    echo   The application stopped with an error. Please read the messages above.
    goto fail
)

echo.
echo   The application has stopped.
echo.
pause
exit /b 0

REM ---------------------------------------------------------------------
REM  Help screen
REM ---------------------------------------------------------------------
:usage
echo   Usage:
echo       setup_and_start.bat                 normal start
echo       setup_and_start.bat --reinstall     reinstall the Python packages
echo       setup_and_start.bat --reset-db      rebuild and reseed the database
echo       setup_and_start.bat --port 8502     use a different port
echo       setup_and_start.bat --help          show this help
echo.
pause
exit /b 0

REM ---------------------------------------------------------------------
REM  Failure exit
REM ---------------------------------------------------------------------
:fail
echo.
echo =======================================================================
echo   SETUP WAS NOT COMPLETED
echo =======================================================================
echo   Please correct the problem described above and run the script again.
echo.
pause
exit /b 1
