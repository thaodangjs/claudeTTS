# Hướng dẫn cài đặt nhanh

## Bước 1: Cài đặt Python

1. Tải Python 3.8+ từ: https://www.python.org/downloads/
2. **QUAN TRỌNG:** Khi cài đặt, tick vào ☑️ "Add Python to PATH"
3. Cài đặt bình thường

## Bước 2: Cài đặt thư viện

Mở Command Prompt tại thư mục dự án (chuột phải → "Open in Terminal"), chạy:

```bash
pip install -r requirements.txt
```

Hoặc click đúp vào file `install.bat`

## Bước 3: Chạy phần mềm

```bash
python tts_automation.py
```

Hoặc click đúp vào file `run.bat`

## Bước 4: Cấu hình (lần đầu)

### Cloudflare R2
1. Đăng nhập Cloudflare → R2
2. Tạo bucket mới
3. Tạo API Token với quyền Read & Write
4. Copy thông tin vào Tab 2 của phần mềm

### Supabase
1. Vào Supabase Dashboard → Settings → API
2. Copy URL và service_role key
3. Nhập vào Tab 2 của phần mềm

## Xong! Bắt đầu sử dụng

1. Tab 1: Chọn truyện và chương
2. Tab 2: Cấu hình (chỉ lần đầu)
3. Tab 3: Bắt đầu xử lý

---

**Lưu ý:** Nếu gặp lỗi "python is not recognized", bạn cần cài lại Python và nhớ tick "Add Python to PATH"
