@echo off
title EditFlow - Video Processing Workflow
echo.
echo  ========================================
echo   EditFlow - Starting...
echo  ========================================
echo.

:: Check if Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

:: Check if venv exists, create if not
if not exist "venv\Scripts\activate.bat" (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [SETUP] Virtual environment created.
    echo.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install dependencies if needed
if not exist "venv\Lib\site-packages\flask" (
    echo  [SETUP] Installing dependencies...
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo  [SETUP] Dependencies installed.
    echo.
)

:: Check if FFmpeg is available
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo  [WARNING] FFmpeg is not in PATH.
    echo  EditFlow requires FFmpeg for video processing.
    echo  Download from: https://ffmpeg.org/download.html
    echo.
)

echo  [OK] Launching EditFlow...
echo  [OK] Open http://localhost:5000 in your browser.
echo.
echo  Press Ctrl+C to stop the server.
echo  ========================================
echo.

python app.py

:: If the server exits, pause so the user can see any errors
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] EditFlow exited with an error.
    pause
)
