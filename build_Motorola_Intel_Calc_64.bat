@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=python"
set "ICON=%~dp0Motorola_Intel_Calc_64.ico"
set "SOURCE=%~dp0Motorola_Intel_Calc_64.py"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] System Python was not found in PATH.
    exit /b 1
)

if not exist "%ICON%" (
    echo [ERROR] Icon not found: %ICON%
    exit /b 1
)

if not exist "%SOURCE%" (
    echo [ERROR] Source not found: %SOURCE%
    exit /b 1
)

"%PYTHON%" -m PyInstaller ^
    --noconfirm --clean --onefile --windowed ^
    --name Motorola_Intel_Calc_64 ^
    --icon "%ICON%" ^
    --add-data "%ICON%;." ^
    --distpath "%~dp0release" ^
    --workpath "%~dp0build\pyinstaller_final" ^
    --specpath "%~dp0build" ^
    "%SOURCE%"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    exit /b 1
)

echo.
echo [OK] Built: %~dp0release\Motorola_Intel_Calc_64.exe
endlocal
