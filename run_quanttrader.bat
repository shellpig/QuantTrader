@echo off
setlocal

cd /d "%~dp0"
set "PYTHONPATH=%CD%"

if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
if exist "%APPDATA%\uv\bin\uv.exe"         set "PATH=%APPDATA%\uv\bin;%PATH%"

echo Starting QuantTrader...
echo URL: http://localhost:8501
echo.

uv run streamlit run src/ui/app.py

echo.
echo QuantTrader has stopped.
pause
