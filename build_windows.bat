@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  JJClicker  —  Windows MSI build script
REM  Run this on a Windows machine with Python 3.10+ installed.
REM ─────────────────────────────────────────────────────────────────────────

echo [1/3] Installing dependencies...
pip install -r requirements_windows.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo [2/3] Building MSI installer...
python setup_cx_freeze.py bdist_msi
if errorlevel 1 (
    echo ERROR: build failed.
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo The .msi installer is in the  dist\  folder.
echo Install it and JJClicker will be placed in:
echo   C:\Program Files\JJClicker\JJClicker.exe
echo.
pause
