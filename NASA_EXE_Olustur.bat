@echo off
chcp 65001 >nul
cd /d "%~dp0"
title NASA Space Apps 2026 - Flame in Freefall EXE Paketleyici

echo ===============================================================================
echo     NASA SPACE APPS CHALLENGE 2026 - FLAME IN FREEFALL
echo     OTOMATIK EXE PROGRAMI DERLEYICI VE PAKETLEYICI (PyInstaller)
echo ===============================================================================
echo.

REM 1. Python Calistiricisini Otomatik Tespit Et
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist "..\.venv\Scripts\python.exe" set "PY=..\.venv\Scripts\python.exe"
if exist "..\..\.venv\Scripts\python.exe" set "PY=..\..\.venv\Scripts\python.exe"
if exist "E:\Yazilim\Python\.venv\Scripts\python.exe" set "PY=E:\Yazilim\Python\.venv\Scripts\python.exe"
if exist "E:\Yazılım\Python\.venv\Scripts\python.exe" set "PY=E:\Yazılım\Python\.venv\Scripts\python.exe"

if "%PY%"=="" set "PY=python"

echo [*] Kullanilan Python: %PY%
"%PY%" --version
echo.

REM 2. Bagimliliklari ve PyInstaller Paketleyicisini Denetle
echo [1/3] Gerekli kutuphaneler denetleniyor ve yukleniyor...
"%PY%" -m pip install --quiet --upgrade pip
"%PY%" -m pip install --quiet -r requirements.txt
"%PY%" -m pip install --quiet pyinstaller
echo [OK] Kutuphaneler hazir.
echo.

REM 3. PyInstaller ile Tum Modulleri ve Verileri Derle
echo [2/3] NASA projesi tum bilesenleriyle EXE programina donusturuluyor...
echo       - Giris Noktasi: flame_in_freefall_app.py (CustomTkinter GUI)
echo       - Fizik Motoru, NTRS Istemcisi, PSI Veritabani, AI Asistan
echo       - NTRS Korpus Verileri (veri/) ve Gorsel Dokumantasyon (docs/)
echo.
"%PY%" -m PyInstaller --noconfirm --clean NASA_Flame_In_Freefall.spec

echo.
echo [3/3] Derleme sonuclari dogrulaniyor...
if exist "dist\NASA_Flame_In_Freefall\NASA_Flame_In_Freefall.exe" (
    echo.
    echo ===============================================================================
    echo [BASARILI] NASA_Flame_In_Freefall.exe basariyla olusturuldu!
    echo Konum: dist\NASA_Flame_In_Freefall\NASA_Flame_In_Freefall.exe
    echo.
    echo Uygulamayi dogrudan baslatmak icin "NASA_Baslat.bat" dosyasina cift tiklayabilir
    echo veya olusturulan dist\NASA_Flame_In_Freefall\ klasorunu kullanabilirsiniz.
    echo ===============================================================================
) else (
    echo.
    echo ===============================================================================
    echo [HATA] EXE olusturma sirasinda bir hata meydana geldi!
    echo Lutfen terminal ciktisindaki hata mesajini inceleyin.
    echo ===============================================================================
)

echo.
pause
