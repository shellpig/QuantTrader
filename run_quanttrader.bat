@echo off
setlocal

cd /d "%~dp0"
set "PYTHONPATH=%CD%"

echo Starting QuantTrader...
echo URL: http://localhost:8501
echo.

uv run streamlit run src/ui/app.py

echo.
echo QuantTrader has stopped.
pause
