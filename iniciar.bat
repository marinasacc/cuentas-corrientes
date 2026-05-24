@echo off
title Cuentas Corrientes - Tu Textil
echo.
echo ========================================
echo   CUENTAS CORRIENTES - Tu Textil
echo ========================================
echo.
echo Iniciando aplicacion...
echo.

cd /d "%~dp0"

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Instala Python desde https://www.python.org/downloads/
    pause
    exit
)

:: Instalar dependencias si hace falta
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando dependencias por primera vez...
    pip install --user flask pandas openpyxl xlrd
    echo.
)

:: Abrir navegador despues de 2 segundos
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5050"

:: Iniciar servidor
echo Servidor corriendo en http://localhost:5050
echo Podes cerrar esta ventana para detener la aplicacion.
echo.
python app.py
pause
