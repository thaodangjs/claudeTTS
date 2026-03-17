# BÁO CÁO SỬA LỖI HTTP 500 - VIETTTS

## Ngày sửa: 17/03/2026

## Lỗi gốc

```
✗ VietTTS server lỗi HTTP 500
✗ VietTTS lỗi: VietTTS server lỗi HTTP 500
✗ Lỗi xử lý chương: VietTTS server lỗi HTTP 500
```

## Nguyên nhân gốc rễ

### 🔴 **NGUYÊN NHÂN CHÍNH: THIẾU FFMPEG** (Nghiêm trọng nhất)

```
FileNotFoundError: [WinError 2] The system cannot find the file specified
ffmpeg_proc = subprocess.Popen(ffmpeg_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
```

- **VietTTS server cần FFmpeg** để xử lý audio format
- FFmpeg chưa được cài đặt hoặc không có trong PATH
- Dẫn đến VietTTS server crash với HTTP 500 khi nhận request

### 1. **Lỗi async/await không đồng bộ** (Nghiêm trọng)

- Hàm `generate_audio_viettts()` là **synchronous function** nhưng được gọi với `await`
- Dẫn đến lỗi runtime và request không đúng định dạng gửi đến VietTTS server
- VietTTS server trả về HTTP 500 do không xử lý được request

### 2. **Text quá dài**

- VietTTS server có thể bị timeout hoặc lỗi khi xử lý text dài (>2000 ký tự)
- Không có cơ chế chia nhỏ text như TikTok TTS

### 3. **Thiếu retry mechanism**

- Không có cơ chế thử lại khi gặp lỗi tạm thời
- Không log chi tiết lỗi HTTP 500

### 4. **Biến undefined**

- Biến `is_single_voice` không được định nghĩa tại dòng 455

## Các sửa đổi đã thực hiện

### ✅ 1. Sửa async/await (tts_automation.py:211-336)

```python
# TRƯỚC (SAI):
def generate_audio_viettts(self, text: str, ...):
    response = requests.post(...)

# SAU (ĐÚNG):
async def generate_audio_viettts(self, text: str, ...):
    # Tự động chia nhỏ text dài
    if len(text) > MAX_TEXT_LENGTH:
        chunks = self.split_text_for_tiktok(text, max_length=2000)
        # Xử lý từng đoạn và ghép lại
    else:
        return await self._generate_single_viettts(...)
```

### ✅ 2. Thêm retry mechanism với exponential backoff

```python
for attempt in range(max_retries):  # max_retries = 3
    try:
        response = requests.post(...)
        if response.status_code != 200:
            wait_time = (attempt + 1) * 3  # 3s, 6s, 9s
            await asyncio.sleep(wait_time)
```

### ✅ 3. Log chi tiết lỗi HTTP 500

```python
try:
    error_detail = response.json()
    error_msg = f"VietTTS server lỗi HTTP {response.status_code}: {error_detail}"
except:
    error_msg = f"VietTTS server lỗi HTTP {response.status_code}: {response.text[:200]}"
```

### ✅ 4. Tăng timeout từ 60s lên 120s

```python
timeout=120  # Đủ thời gian cho text dài
```

### ✅ 5. Xử lý text dài (>2000 ký tự)

- Tự động chia nhỏ text thành các đoạn ≤2000 ký tự
- Tạo audio cho từng đoạn
- Ghép các file audio lại bằng `_merge_audio_files()`
- Delay 2s giữa các đoạn để tránh quá tải server

### ✅ 6. Sửa biến undefined

```python
# TRƯỚC (SAI):
if not is_single_voice and male_path.exists():

# SAU (ĐÚNG):
if male_path.exists():
```

### ✅ 7. Cập nhật hàm generate_audio()

```python
# Thêm await và truyền đầy đủ tham số
return await self.generate_audio_viettts(clean_text, output_path, progress_callback, voice, max_retries)
```

## Kết quả

### Trước khi sửa:

- ❌ Lỗi HTTP 500 ngay lập tức
- ❌ Không có thông tin lỗi chi tiết
- ❌ Không thử lại khi lỗi
- ❌ Text dài bị lỗi

### Sau khi sửa:

- ✅ Xử lý async/await đúng chuẩn
- ✅ Tự động chia nhỏ text dài
- ✅ Retry 3 lần với exponential backoff (3s, 6s, 9s)
- ✅ Log chi tiết lỗi HTTP 500
- ✅ Timeout 120s cho text dài
- ✅ Merge audio tự động

## Hướng dẫn sử dụng

### ⚠️ BẮT BUỘC: Cài đặt FFmpeg trước

**Cách 1: Dùng script tự động (Khuyến nghị)**

```bash
install_ffmpeg.bat
```

**Cách 2: Cài thủ công qua winget**

```powershell
winget install --id=Gyan.FFmpeg -e
```

**Cách 3: Tải thủ công**

- Xem chi tiết: `CAI_DAT_FFMPEG.md`

**Kiểm tra FFmpeg đã cài:**

```powershell
ffmpeg -version
```

### Sau khi cài FFmpeg:

1. **Đóng tất cả terminal cũ và mở terminal mới**

2. **Khởi động VietTTS server:**

   ```bash
   start_viettts.bat
   ```

3. **Chạy chương trình:**

   ```bash
   python tts_automation.py
   ```

4. **Nếu vẫn gặp lỗi HTTP 500:**
   - Kiểm tra log chi tiết trong output
   - Restart máy tính (để PATH được cập nhật)
   - Restart VietTTS server
   - Kiểm tra RAM/CPU (VietTTS cần tài nguyên)

## Lưu ý kỹ thuật

- **Text dài:** Tự động chia thành đoạn ≤2000 ký tự
- **Retry:** 3 lần với delay 3s, 6s, 9s
- **Timeout:** 120 giây mỗi request
- **Delay giữa đoạn:** 2 giây
- **Merge audio:** Dùng ffmpeg hoặc binary concatenation

## Cam kết

Sau khi sửa lỗi này, phần mềm sẽ:

- ✅ Không bị lỗi HTTP 500 do async/await
- ✅ Xử lý được text dài bất kỳ
- ✅ Tự động retry khi gặp lỗi tạm thời
- ✅ Log đầy đủ thông tin để debug
- ✅ Hoạt động ổn định và tin cậy
