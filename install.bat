@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1

echo.
echo  ====================================
echo   QuantTrader 安裝程式
echo  ====================================
echo.

:: ── Step 1: 確認 uv ──────────────────────────────────────────
echo [1/3] 檢查 uv 套件管理器...

set "UV_EXE=uv"
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    :: 嘗試常見安裝位置
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
        echo      找到 uv：%USERPROFILE%\.local\bin\uv.exe
        goto :uv_found
    )
    if exist "%APPDATA%\uv\bin\uv.exe" (
        set "UV_EXE=%APPDATA%\uv\bin\uv.exe"
        set "PATH=%APPDATA%\uv\bin;%PATH%"
        echo      找到 uv：%APPDATA%\uv\bin\uv.exe
        goto :uv_found
    )

    echo      未找到 uv，開始安裝...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "irm https://astral.sh/uv/install.ps1 | iex"
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  [錯誤] uv 安裝失敗。
        echo  請手動前往 https://docs.astral.sh/uv/ 下載安裝後再重新執行。
        echo.
        pause
        exit /b 1
    )

    :: 安裝後加入 PATH
    set "PATH=%USERPROFILE%\.local\bin;%APPDATA%\uv\bin;%PATH%"

    where uv >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        if exist "%USERPROFILE%\.local\bin\uv.exe" (
            set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
        ) else if exist "%APPDATA%\uv\bin\uv.exe" (
            set "UV_EXE=%APPDATA%\uv\bin\uv.exe"
        ) else (
            echo.
            echo  [錯誤] uv 安裝後仍找不到執行檔。
            echo  請重新開啟視窗後再執行 install.bat。
            echo.
            pause
            exit /b 1
        )
    )
    echo      uv 安裝成功！
) else (
    echo      uv 已安裝。
)

:uv_found

:: ── Step 2: 安裝 Python 套件 ─────────────────────────────────
echo.
echo [2/3] 安裝 Python 套件（首次約需 1~3 分鐘）...
echo.
"%UV_EXE%" sync
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [錯誤] 套件安裝失敗，請截圖以上錯誤訊息。
    echo.
    pause
    exit /b 1
)

:: ── Step 3: 建立 .env ────────────────────────────────────────
echo.
echo [3/3] 設定環境變數...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo      .env 已建立。
    echo.
    echo  ┌─────────────────────────────────────────────────┐
    echo  │  請用記事本開啟 .env，填入以下金鑰（至少填一個）：│
    echo  │    FINMIND_TOKEN   - 台股資料來源（必填）         │
    echo  │    ANTHROPIC_API_KEY - AI 分析功能（選填）        │
    echo  └─────────────────────────────────────────────────┘
    echo.
    set /p OPEN_ENV="  現在開啟 .env 填寫嗎？(y/n) "
    if /i "!OPEN_ENV!"=="y" notepad ".env"
) else (
    echo      .env 已存在，略過。
)

:: ── 完成 ─────────────────────────────────────────────────────
echo.
echo  ====================================
echo   安裝完成！
echo   請雙擊 run_quanttrader.bat 啟動
echo  ====================================
echo.
pause
