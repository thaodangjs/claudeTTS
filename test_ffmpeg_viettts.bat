@echo off
echo ========================================
echo   TEST FFMPEG VA VIETTTS
echo ========================================
echo.

REM Test 1: Kiem tra FFmpeg
echo [1/3] Kiem tra FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ FFmpeg chua duoc cai dat!
    echo.
    echo Vui long chay: install_ffmpeg.bat
    echo Hoac xem huong dan: CAI_DAT_FFMPEG.md
    echo.
    pause
    exit /b 1
) else (
    echo ✓ FFmpeg da duoc cai dat
)
echo.

REM Test 2: Kiem tra VietTTS server
echo [2/3] Kiem tra VietTTS server...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8298/health' -UseBasicParsing -TimeoutSec 5; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo ✗ VietTTS server chua chay!
    echo.
    echo Vui long chay: start_viettts.bat
    echo.
    pause
    exit /b 1
) else (
    echo ✓ VietTTS server dang chay
)
echo.

REM Test 3: Test tao audio nho
echo [3/3] Test tao audio mau...
powershell -Command "$body = @{ model='tts-1'; input='Xin chao, day la test'; voice='5'; speed=1.0; response_format='wav' } | ConvertTo-Json; try { $response = Invoke-WebRequest -Uri 'http://localhost:8298/v1/audio/speech' -Method POST -Headers @{'Authorization'='Bearer viet-tts'; 'Content-Type'='application/json'} -Body $body -UseBasicParsing -TimeoutSec 30; if ($response.StatusCode -eq 200) { [System.IO.File]::WriteAllBytes('test_audio.wav', $response.Content); exit 0 } else { exit 1 } } catch { Write-Host $_.Exception.Message; exit 1 }"
if %errorlevel% neq 0 (
    echo ✗ Test tao audio THAT BAI!
    echo.
    echo Nguyen nhan co the:
    echo - FFmpeg chua duoc them vao PATH
    echo - VietTTS server gap loi
    echo.
    echo Giai phap:
    echo 1. Dong tat ca terminal
    echo 2. Mo terminal moi
    echo 3. Restart VietTTS server
    echo 4. Chay lai test nay
    echo.
    pause
    exit /b 1
) else (
    echo ✓ Test tao audio THANH CONG!
    echo ✓ File mau: test_audio.wav
    if exist test_audio.wav (
        del test_audio.wav
    )
)
echo.

echo ========================================
echo   TAT CA TEST THANH CONG!
echo ========================================
echo.
echo Ban co the chay chuong trinh chinh:
echo   python tts_automation.py
echo.

pause
