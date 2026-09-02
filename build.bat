@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%~dp0Toolchain\python\python.exe"
set "ICON=%~dp0MotorolaIntelCalc64.ico"
set "SOURCE=%~dp0MotorolaIntelCalc64.py"

if not exist "%PYTHON%" (
    echo [ERROR] Local Python was not found: %PYTHON%
    exit /b 1
)

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is missing from Toolchain\python.
    echo Install it: "%PYTHON%" -m pip install pyinstaller
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
    --name MotorolaIntelCalc64 ^
    --icon "%ICON%" ^
    --add-data "%ICON%;." ^
    --distpath "%~dp0Out" ^
    --workpath "%~dp0build\pyinstaller_final" ^
    --specpath "%~dp0build" ^
    "%SOURCE%"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    exit /b 1
)

echo.
echo [OK] Built: %~dp0Out\MotorolaIntelCalc64.exe
endlocal
