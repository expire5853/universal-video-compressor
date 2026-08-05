@echo off
setlocal

where uv.exe >nul 2>&1
if errorlevel 1 (
    echo uv.exe was not found in PATH.
    echo Install uv from https://docs.astral.sh/uv/ and try again.
    pause
    exit /b 1
)

uv run "%~dp0video_compressor_tui.py" %*
if errorlevel 1 (
    echo.
    echo Video Compressor TUI exited with an error.
    pause
)
