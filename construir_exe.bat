@echo off
setlocal
cd /d "%~dp0"

set PYTHONDONTWRITEBYTECODE=1
set /p VERSION=<VERSION

echo.
echo === Organizador %VERSION% ===
echo.

echo [1/6] Dependencias, incluidos pytest y pyinstaller...
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

echo [2/6] Tests...
python -m pytest app\tests -q -p no:cacheprovider
if errorlevel 1 goto :error

echo [3/6] Limpiando armados anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [4/6] Generando Organizador.exe...
python -m PyInstaller --noconfirm --onefile --name Organizador --paths app --add-data "app\dashboard_app.html;." --add-data "app\static;static" app\dashboard.py
if errorlevel 1 goto :error

echo [5/6] Calculando SHA-256 del exe...
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 'dist\Organizador.exe').Hash" > dist\_sha.txt
if errorlevel 1 goto :error
set /p SHA=<dist\_sha.txt
del dist\_sha.txt
echo %SHA%  Organizador.exe>dist\Organizador.exe.sha256

echo [6/6] Armando el paquete para compartir...
powershell -NoProfile -Command "Get-ChildItem -Path 'app' -Recurse -Directory | Where-Object { $_.Name -in '__pycache__','.pytest_cache' } | Remove-Item -Recurse -Force"
mkdir "dist\Organizador-%VERSION%"
copy /y dist\Organizador.exe "dist\Organizador-%VERSION%\" >nul
copy /y dist\Organizador.exe.sha256 "dist\Organizador-%VERSION%\" >nul
copy /y README.md "dist\Organizador-%VERSION%\" >nul
copy /y THIRD_PARTY_NOTICES.md "dist\Organizador-%VERSION%\" >nul
copy /y VERSION "dist\Organizador-%VERSION%\" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'app','Organizador.spec','construir_exe.bat','iniciar.bat','requirements.txt','requirements-dev.txt','README.md','THIRD_PARTY_NOTICES.md','VERSION' -DestinationPath 'dist\Organizador-%VERSION%\Organizador-%VERSION%-fuente.zip'"
if errorlevel 1 goto :error
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\Organizador-%VERSION%\*' -DestinationPath 'dist\Organizador-%VERSION%.zip'"
if errorlevel 1 goto :error

echo.
echo Listo para distribuir:
echo   dist\Organizador-%VERSION%.zip
echo   dist\Organizador.exe
echo   SHA-256 del exe: %SHA%
echo.
echo El zip trae el ejecutable, el README, las licencias y la fuente.
echo Si compartis el exe, acompanalo con la fuente como pide la licencia AGPL-3.0.
exit /b 0

:error
echo.
echo FALLO: el paquete NO se genero. Revisa los mensajes de arriba.
exit /b 1
