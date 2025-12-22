@echo off
chcp 65001 >nul
color 0A
title 🎵 CutFileMp3 - Audio Splitter

cls
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║                                                        ║
echo ║         🎵  CutFileMp3 - Audio Splitter  🎵           ║
echo ║                                                        ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo ┌────────────────────────────────────────────────────────┐
echo │  ⚡ Starting application...                            │
echo │  🌐 Browser will open at: http://127.0.0.1:5000       │
echo │  ⏹️  Press Ctrl+C to stop the server                  │
echo └────────────────────────────────────────────────────────┘
echo.

python app.py

if errorlevel 1 (
    color 0C
    echo.
    echo ╔════════════════════════════════════════════════════════╗
    echo ║  ❌ ERROR: Failed to start application                ║
    echo ╚════════════════════════════════════════════════════════╝
    echo.
    echo Possible issues:
    echo  - Python is not installed or not in PATH
    echo  - Flask is not installed (run: pip install flask)
    echo  - FFmpeg is not installed
    echo.
    pause
    exit /b 1
)

pause
