@echo off
chcp 65001 >nul
cd /d "%~dp0"
title NASA Flame in Freefall 2026 - Baslatici

REM 1. Eger derlenmis EXE varsa dogrudan tek tikla calistir
if exist "dist\NASA_Flame_In_Freefall\NASA_Flame_In_Freefall.exe" (
    start "" "dist\NASA_Flame_In_Freefall\NASA_Flame_In_Freefall.exe"
    exit /b
)

REM 2. Eger bagil .venv varsa pythonw ile arka planda sessiz calistir
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "flame_in_freefall_app.py"
    exit /b
)

if exist "..\.venv\Scripts\pythonw.exe" (
    start "" "..\.venv\Scripts\pythonw.exe" "flame_in_freefall_app.py"
    exit /b
)

if exist "E:\Yazılım\Python\.venv\Scripts\pythonw.exe" (
    start "" "E:\Yazılım\Python\.venv\Scripts\pythonw.exe" "flame_in_freefall_app.py"
    exit /b
)

if exist "E:\Yazilim\Python\.venv\Scripts\pythonw.exe" (
    start "" "E:\Yazilim\Python\.venv\Scripts\pythonw.exe" "flame_in_freefall_app.py"
    exit /b
)

REM 3. Sistem varsayilan python'u ile calistir
start "" pythonw "flame_in_freefall_app.py"
exit /b
