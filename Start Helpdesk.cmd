@echo off
setlocal
cd /d "%~dp0"
title UK Regulation Helpdesk
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.12 run_local.py
    goto done
)
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3.11 run_local.py
    goto done
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    python run_local.py
    goto done
)
echo Install Python 3.12 from https://www.python.org/downloads/windows/
echo Then extract this ZIP to a folder and double-click this file again.
:done
echo.
echo You may close this window. To restart, double-click Start Helpdesk.cmd.
pause
