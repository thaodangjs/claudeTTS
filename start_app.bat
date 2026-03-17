@echo off
echo ========================================
echo   KHOI DONG TTS AUTOMATION
echo ========================================
echo.

REM Chuyen den thu muc chinh
cd /d "%~dp0"

REM Khoi dong phan mem
echo Dang khoi dong phan mem...
echo.
python tts_automation.py

pause
