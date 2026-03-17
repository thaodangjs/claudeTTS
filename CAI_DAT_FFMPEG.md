# HƯỚNG DẪN CÀI ĐẶT FFMPEG CHO WINDOWS

## Nguyên nhân lỗi HTTP 500

VietTTS server cần **FFmpeg** để xử lý audio, nhưng FFmpeg chưa được cài đặt hoặc không có trong PATH.

Lỗi từ VietTTS server:
```
FileNotFoundError: [WinError 2] The system cannot find the file specified
ffmpeg_proc = subprocess.Popen(ffmpeg_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
```

## Cách 1: Cài đặt FFmpeg qua Chocolatey (Khuyến nghị - Nhanh nhất)

### Bước 1: Cài Chocolatey (nếu chưa có)
Mở PowerShell **với quyền Administrator** và chạy:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### Bước 2: Cài FFmpeg
```powershell
choco install ffmpeg -y
```

### Bước 3: Kiểm tra
Mở PowerShell mới và chạy:
```powershell
ffmpeg -version
```

## Cách 2: Tải và cài thủ công

### Bước 1: Tải FFmpeg
1. Truy cập: https://www.gyan.dev/ffmpeg/builds/
2. Tải file: **ffmpeg-release-essentials.zip**

### Bước 2: Giải nén
1. Giải nén file zip vào `C:\ffmpeg`
2. Đường dẫn ffmpeg.exe sẽ là: `C:\ffmpeg\bin\ffmpeg.exe`

### Bước 3: Thêm vào PATH
1. Nhấn `Windows + R`, gõ `sysdm.cpl`, Enter
2. Tab **Advanced** → **Environment Variables**
3. Trong **System variables**, tìm **Path**, click **Edit**
4. Click **New**, thêm: `C:\ffmpeg\bin`
5. Click **OK** tất cả các cửa sổ

### Bước 4: Kiểm tra
Mở PowerShell **MỚI** và chạy:
```powershell
ffmpeg -version
```

## Cách 3: Cài FFmpeg vào thư mục dự án (Nhanh - Không cần PATH)

### Tạo script tự động tải FFmpeg:
```powershell
# Chạy trong PowerShell tại thư mục dự án
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zipPath = "ffmpeg.zip"
$extractPath = "ffmpeg"

Write-Host "Đang tải FFmpeg..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $ffmpegUrl -OutFile $zipPath

Write-Host "Đang giải nén..." -ForegroundColor Yellow
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

Write-Host "Đang cấu hình..." -ForegroundColor Yellow
$ffmpegBin = Get-ChildItem -Path $extractPath -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
$ffmpegDir = $ffmpegBin.Directory.FullName

# Thêm vào PATH tạm thời
$env:Path += ";$ffmpegDir"

Write-Host "✓ Đã cài FFmpeg tại: $ffmpegDir" -ForegroundColor Green
Write-Host "Kiểm tra: ffmpeg -version" -ForegroundColor Cyan

# Dọn dẹp
Remove-Item $zipPath -Force
```

Sau đó chạy:
```powershell
ffmpeg -version
```

## Sau khi cài FFmpeg

### 1. Restart VietTTS server
```bash
# Tắt server cũ (Ctrl+C)
# Chạy lại:
start_viettts.bat
```

### 2. Chạy lại chương trình
```bash
python tts_automation.py
```

## Kiểm tra FFmpeg đã hoạt động

Chạy lệnh test:
```powershell
ffmpeg -version
```

Kết quả mong đợi:
```
ffmpeg version 6.x.x Copyright (c) 2000-2024 the FFmpeg developers
...
```

## Nếu vẫn lỗi

1. **Đóng tất cả PowerShell/CMD** và mở lại
2. **Restart máy tính** để PATH được cập nhật
3. Kiểm tra lại: `ffmpeg -version`
4. Restart VietTTS server

## Lưu ý quan trọng

- ✅ FFmpeg **BẮT BUỘC** cho VietTTS server
- ✅ Phải thêm vào **System PATH** hoặc chạy trong thư mục có ffmpeg.exe
- ✅ Sau khi cài, **phải mở PowerShell mới** để PATH có hiệu lực
- ✅ VietTTS server **phải restart** sau khi cài FFmpeg
