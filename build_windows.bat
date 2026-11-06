@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name CitySupportAssistant --add-data "assets;assets" app.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
echo.
echo Executable created at: dist\CitySupportAssistant.exe
endlocal
