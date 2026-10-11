@echo off

setlocal

cd /d "%~dp0"

python -m pip install -r requirements.txt pyinstaller

if exist dist rmdir /s /q dist

if exist build rmdir /s /q build

python -m PyInstaller --noconfirm --onefile --name Organizador --paths app --add-data "app\dashboard_app.html;." --add-data "app\static;static" app\dashboard.py

if errorlevel 1 exit /b 1

echo.

echo Listo: dist\Organizador.exe

