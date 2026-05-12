@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  ====================================
echo   QuantTrader Setup
echo  ====================================
echo.

echo [1/3] Checking uv package manager...

set "UV_EXE=uv"
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
        goto :uv_found
    )
    if exist "%APPDATA%\uv\bin\uv.exe" (
        set "UV_EXE=%APPDATA%\uv\bin\uv.exe"
        set "PATH=%APPDATA%\uv\bin;%PATH%"
        goto :uv_found
    )

    echo      uv not found. Installing...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  [ERROR] Failed to install uv.
        echo  Please visit https://docs.astral.sh/uv/ and install manually, then re-run.
        echo.
        pause
        exit /b 1
    )

    set "PATH=%USERPROFILE%\.local\bin;%APPDATA%\uv\bin;%PATH%"

    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
        goto :uv_found
    )
    if exist "%APPDATA%\uv\bin\uv.exe" (
        set "UV_EXE=%APPDATA%\uv\bin\uv.exe"
        goto :uv_found
    )

    echo.
    echo  [ERROR] uv installed but not found. Close and re-run install.bat.
    echo.
    pause
    exit /b 1
) else (
    echo      uv already installed.
)

:uv_found
echo      OK

echo.
echo [2/3] Installing Python packages (may take a few minutes)...
echo.
"%UV_EXE%" sync
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Package installation failed.
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Setting up .env config...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo      .env created.
    echo.
    echo      Please open .env and fill in your API keys:
    echo        FINMIND_TOKEN    - Taiwan stock data (required)
    echo        ANTHROPIC_API_KEY - AI features (optional)
    echo.
    set /p OPEN_ENV="      Open .env in Notepad now? (y/n) "
    if /i "!OPEN_ENV!"=="y" notepad ".env"
) else (
    echo      .env already exists, skipping.
)

echo.
echo  ====================================
echo   Setup complete!
echo   Double-click run_quanttrader.bat to start.
echo  ====================================
echo.
pause