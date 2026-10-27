@echo off
setlocal
where python >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or later is required.
    echo Purpose: Python runs TubeQueue.
    echo Install it from https://www.python.org/downloads/ and enable the PATH option.
    set "tubequeue_exit_code=1"
    goto :finish
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or later is required.
    echo Purpose: Python runs TubeQueue.
    echo Install or update it from https://www.python.org/downloads/ and enable the PATH option.
    set "tubequeue_exit_code=1"
    goto :finish
)
python "%~dp0player.py" %*
set "tubequeue_exit_code=%errorlevel%"
:finish
echo.
echo Press any key to close this window...
pause >nul
exit /b %tubequeue_exit_code%
