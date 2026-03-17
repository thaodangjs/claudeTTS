@echo off
echo ========================================
echo   CAI DAT FFMPEG
echo ========================================
echo.

REM Kiem tra winget
winget --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Loi: Khong tim thay winget
    echo Vui long cai dat App Installer tu Microsoft Store
    pause
    exit /b 1
)

echo Dang cai dat ffmpeg...
winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements

echo.
echo ========================================
echo   CAI DAT HOAN TAT
echo ========================================
echo.
echo Vui long DONG va MO LAI terminal de cap nhat PATH
echo.

pause
