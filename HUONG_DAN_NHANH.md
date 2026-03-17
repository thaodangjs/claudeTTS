# 🎤 HƯỚNG DẪN SỬ DỤNG NHANH - TTS AUTOMATION VỚI VIETTTS

## 📋 Các lệnh cần chạy mỗi lần sử dụng

### Bước 1: Khởi động VietTTS Server ⚡

Mở **Terminal 1** và chạy:

```bash
cd d:\Dev\Full-stack\ttByClaude\viet-tts
python -m uvicorn viettts.server:app --host 0.0.0.0 --port 8298
```

**⚠️ Giữ terminal này mở** trong suốt quá trình sử dụng!

Khi thấy dòng này là đã sẵn sàng:
```
INFO:     Uvicorn running on http://0.0.0.0:8298
```

---

### Bước 2: Chạy phần mềm TTS Automation 🚀

Mở **Terminal 2** (terminal mới) và chạy:

```bash
cd d:\Dev\Full-stack\ttByClaude
python tts_automation.py
```

---

## 🎯 Sử dụng phần mềm

### Tab 1 - Chọn truyện & chương
1. Chọn truyện từ danh sách bên trái
2. Chọn các chương muốn tạo audio bên phải
3. Có thể dùng "Chọn tất cả"

### Tab 2 - Cấu hình
- ✅ **VietTTS** đã được chọn sẵn
- **Giọng nữ:** `0` (mặc định)
- **Giọng nam:** `1` (mặc định)
- Để xem danh sách giọng: `viettts show-voices`

### Tab 3 - Xử lý
- Nhấn **🚀 Bắt đầu xử lý**
- Theo dõi tiến độ trong log
- File audio sẽ được lưu tại: `audio_output/Ten_Truyen/`

---

## 🎭 Tùy chỉnh giọng đọc

### Xem danh sách giọng:
```bash
viettts show-voices
```

### Chọn giọng khác:
- Vào **Tab 2 - Cấu hình**
- Nhập số/tên giọng vào ô **Giọng nữ** và **Giọng nam**

---

## 📁 Kết quả

File audio được lưu tại:
```
audio_output/
  └── Ten_Truyen/
      ├── Ten_Truyen_chuong_0001_male.mp3   (giọng nam)
      ├── Ten_Truyen_chuong_0001_female.mp3 (giọng nữ)
      ├── Ten_Truyen_chuong_0002_male.mp3
      └── Ten_Truyen_chuong_0002_female.mp3
```

---

## ⚠️ Lưu ý quan trọng

1. **VietTTS server phải đang chạy** (Terminal 1) trước khi bắt đầu xử lý
2. **KHÔNG TẮT** Terminal 1 khi đang tạo audio
3. Nếu gặp lỗi "VietTTS server chưa chạy", kiểm tra lại Terminal 1
4. Mỗi lần khởi động lại máy cần chạy lại Bước 1

---

## 🆘 Xử lý lỗi thường gặp

### ❌ "VietTTS server chưa chạy"
→ Chạy lại Bước 1 (khởi động VietTTS server)

### ❌ "No module named 'viettts'"
→ Cài lại VietTTS:
```bash
cd d:\Dev\Full-stack\ttByClaude\viet-tts
pip install -e .
```

### ❌ Model tải lâu lần đầu
→ Bình thường, VietTTS tải model 1.26GB lần đầu tiên (chỉ 1 lần)

---

## 🔧 Cài đặt lần đầu (chỉ 1 lần)

Nếu chưa cài VietTTS:

```bash
cd d:\Dev\Full-stack\ttByClaude
git clone https://github.com/dangvansam/viet-tts.git
cd viet-tts
pip install -e .
```

Cài các thư viện cho phần mềm:
```bash
cd d:\Dev\Full-stack\ttByClaude
pip install edge-tts boto3 gtts pyttsx3 websockets==12
```
