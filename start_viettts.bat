@echo off
echo ========================================
echo   KHOI DONG VIETTTS SERVER
echo ========================================
echo.

REM Tat process cu neu co
echo [1/3] Kiem tra va tat process cu...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8298') do (
    echo Dang tat process cu: %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Chuyen den thu muc viet-tts
echo [2/3] Chuyen den thu muc viet-tts...
cd /d "%~dp0viet-tts"

REM Khoi dong server
echo [3/3] Khoi dong VietTTS server...
echo.
echo ========================================
echo   SERVER DANG CHAY TAI: http://localhost:8298
echo   Nhan CTRL+C de dung server
echo ========================================
echo.

python -m uvicorn viettts.server:app --host 0.0.0.0 --port 8298

pause
