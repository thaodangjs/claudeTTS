# TTS Automation Tool - Chuyển đổi truyện thành audio tự động

Phần mềm Windows tự động chuyển đổi truyện ma thành file audio MP3 sử dụng Edge-TTS (miễn phí), upload lên Cloudflare R2 và cập nhật Supabase.

## Tính năng

✅ **Nhiều phương án TTS miễn phí**

- **Edge-TTS** (Microsoft) - Chất lượng tốt nhất, giọng nam/nữ tiếng Việt
- **Google TTS (gTTS)** - Ổn định hơn, chỉ giọng nữ
- **pyttsx3** - Hoàn toàn offline, không cần internet

✅ **Giao diện thân thiện** - Dễ sử dụng, không cần kiến thức IT

✅ **Chọn lọc linh hoạt** - Chọn truyện và chương cần xuất audio

✅ **Upload tự động lên Cloudflare R2** - Tổ chức theo thư mục truyện

✅ **Cập nhật Supabase** - Tự động điền URL audio vào bảng `chapter_audios`

✅ **Rate limiting** - Tránh bị Edge chặn IP với delay tùy chỉnh

✅ **Chất lượng audio tối ưu** - File MP3 nhẹ nhưng rõ ràng

## Cài đặt

### 1. Cài đặt Python

Tải và cài đặt Python 3.8+ từ [python.org](https://www.python.org/downloads/)

**Lưu ý:** Khi cài đặt, nhớ tick vào "Add Python to PATH"

### 2. Cài đặt dependencies

Mở Command Prompt hoặc PowerShell tại thư mục dự án và chạy:

```bash
pip install -r requirements.txt
```

### 3. Chuẩn bị dữ liệu

Đảm bảo có 3 file JSON trong thư mục `myData/`:

- `stories_rows.json` - Danh sách truyện
- `chapters_private_rows.json` - Danh sách chương
- `chapters_rows.json` (nếu có)

## Sử dụng

### 1. Chạy phần mềm

```bash
python tts_automation.py
```

### 2. Quy trình sử dụng

#### **Tab 1: Chọn truyện & chương**

1. Chọn truyện từ danh sách bên trái
2. Danh sách chương sẽ hiển thị bên phải
3. Chọn các chương cần xuất audio (có thể chọn nhiều)
4. Sử dụng nút "Chọn tất cả" hoặc "Bỏ chọn tất cả" nếu cần

#### **Tab 2: Cấu hình**

**TTS Engine:**

- Chọn phương án TTS phù hợp:
  - **Edge-TTS** (Khuyến nghị) - Chất lượng tốt nhất, có giọng nam/nữ
  - **gTTS** (Dự phòng) - Khi bị lỗi 403 từ Edge-TTS
  - **pyttsx3** (Offline) - Không cần internet, chất lượng thấp

**Cloudflare R2 (Tùy chọn):**

- ☑️ Bật upload lên R2
- Endpoint URL: `https://<account-id>.r2.cloudflarestorage.com`
- Access Key ID: Lấy từ Cloudflare Dashboard
- Secret Access Key: Lấy từ Cloudflare Dashboard
- Bucket Name: Tên bucket của bạn
- Public URL: `https://your-domain.com` hoặc R2 public URL

**Supabase (Tùy chọn):**

- ☑️ Bật cập nhật Supabase
- Supabase URL: `https://your-project.supabase.co`
- Supabase Key: Service role key (anon key cũng được nếu có RLS phù hợp)

**Rate Limiting:**

- Delay giữa các chương: 3-10 giây (khuyến nghị 3-5 giây)
- Delay giữa giọng nam/nữ: 1-2 giây

#### **Tab 3: Xử lý**

1. Kiểm tra thông tin truyện và số chương đã chọn
2. Nhấn "🚀 Bắt đầu xử lý"
3. Theo dõi tiến độ qua thanh progress bar và log
4. Chờ đợi hoàn thành (có thể mất vài phút đến vài giờ tùy số lượng chương)

### 3. Kết quả

**File audio được lưu tại:**

```
audio_output/
├── Tên_Truyện_1/
│   ├── Tên_Truyện_1_chuong_0001_male.mp3
│   ├── Tên_Truyện_1_chuong_0001_female.mp3
│   ├── Tên_Truyện_1_chuong_0002_male.mp3
│   ├── Tên_Truyện_1_chuong_0002_female.mp3
│   └── ...
└── Tên_Truyện_2/
    └── ...
```

**Trên Cloudflare R2:**

```
audio/
├── Tên_Truyện_1/
│   ├── Tên_Truyện_1_chuong_0001_male.mp3
│   ├── Tên_Truyện_1_chuong_0001_female.mp3
│   └── ...
└── Tên_Truyện_2/
    └── ...
```

**Trong Supabase (bảng `chapter_audios`):**
| id | chapter_id | voice | audio_url | created_at | updated_at |
|----|------------|-------|-----------|------------|------------|
| ... | uuid-1 | male | https://... | ... | ... |
| ... | uuid-1 | female | https://... | ... | ... |

## Cấu hình Cloudflare R2

### 1. Tạo R2 Bucket

1. Đăng nhập Cloudflare Dashboard
2. Vào **R2** → **Create bucket**
3. Đặt tên bucket (ví dụ: `truyen-audio`)

### 2. Tạo API Token

1. Vào **R2** → **Manage R2 API Tokens**
2. **Create API Token**
3. Chọn quyền: **Object Read & Write**
4. Lưu lại **Access Key ID** và **Secret Access Key**

### 3. Cấu hình Public Access (nếu cần)

1. Vào bucket → **Settings**
2. **Public Access** → **Allow Access**
3. Hoặc kết nối Custom Domain

## Cấu hình Supabase

### 1. Lấy credentials

1. Vào Supabase Dashboard
2. **Settings** → **API**
3. Copy **URL** và **service_role key**

### 2. Kiểm tra bảng `chapter_audios`

Đảm bảo bảng có cấu trúc:

```sql
CREATE TABLE chapter_audios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id uuid NOT NULL REFERENCES chapters_private(id),
  voice text NOT NULL CHECK (voice IN ('male', 'female')),
  audio_url text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(chapter_id, voice)
);
```

## Lưu ý quan trọng

⚠️ **Rate Limiting:**

- Edge-TTS là dịch vụ miễn phí, nên cần delay hợp lý tránh bị chặn IP
- Khuyến nghị: 3-5 giây giữa các chương, 1-2 giây giữa giọng nam/nữ
- Nếu có nhiều chương, nên chia nhỏ batch xử lý

⚠️ **Dung lượng:**

- Mỗi chương tạo 2 file MP3 (nam + nữ)
- Ước tính: ~500KB - 2MB/file tùy độ dài chương
- Đảm bảo đủ dung lượng ổ cứng và R2 bucket

⚠️ **Kết nối mạng:**

- Cần kết nối internet ổn định
- Upload R2 có thể mất thời gian với file lớn

⚠️ **Bảo mật:**

- Không chia sẻ API keys/tokens
- Không commit file `.env` hoặc credentials lên Git

## Xử lý lỗi thường gặp

### Lỗi: "Module not found"

```bash
pip install -r requirements.txt
```

### Lỗi: "Permission denied" khi upload R2

- Kiểm tra API token có quyền **Object Read & Write**
- Kiểm tra bucket name đúng

### Lỗi: "Supabase insert failed"

- Kiểm tra service_role key
- Kiểm tra RLS policies cho bảng `chapter_audios`
- Đảm bảo `chapter_id` tồn tại trong bảng `chapters_private`

### Audio không rõ ràng

- Edge-TTS đã tối ưu chất lượng
- Có thể do nội dung chương chứa ký tự đặc biệt
- Kiểm tra log để xem text đã được làm sạch chưa

## Roadmap

- [ ] Hỗ trợ pause/resume
- [ ] Xuất báo cáo chi tiết
- [ ] Hỗ trợ nhiều giọng đọc hơn
- [ ] Tối ưu tốc độ xử lý song song
- [ ] Tự động retry khi lỗi

## Hỗ trợ

Nếu gặp vấn đề, vui lòng:

1. Kiểm tra log trong tab "Xử lý"
2. Kiểm tra file JSON trong `myData/` có đúng format không
3. Kiểm tra kết nối mạng
4. Kiểm tra credentials R2 và Supabase

## License

MIT License - Tự do sử dụng cho mục đích cá nhân và thương mại.

---

**Phát triển bởi:** AI Assistant
**Phiên bản:** 1.0.0
**Ngày cập nhật:** 2026-03-17
