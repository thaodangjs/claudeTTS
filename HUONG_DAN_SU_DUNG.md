# Hướng dẫn sử dụng chi tiết - TTS Automation

## 📋 Mục lục

1. [Cài đặt](#cài-đặt)
2. [Cấu hình lần đầu](#cấu-hình-lần-đầu)
3. [Sử dụng phần mềm](#sử-dụng-phần-mềm)
4. [Xử lý lỗi](#xử-lý-lỗi)
5. [Tips & Tricks](#tips--tricks)

---

## Cài đặt

### 1. Cài Python (nếu chưa có)

**Download:** https://www.python.org/downloads/

⚠️ **QUAN TRỌNG:** Khi cài đặt Python:

- ✅ Tick vào **"Add Python to PATH"**
- ✅ Chọn **"Install Now"**

**Kiểm tra cài đặt thành công:**

```bash
python --version
```

Kết quả: `Python 3.x.x`

### 2. Cài đặt thư viện

**Cách 1:** Click đúp vào file `install.bat`

**Cách 2:** Mở Command Prompt tại thư mục dự án:

```bash
pip install -r requirements.txt
```

**Thời gian:** Khoảng 1-2 phút

---

## Cấu hình lần đầu

### A. Cloudflare R2 (Tùy chọn - để upload audio lên cloud)

#### Bước 1: Tạo R2 Bucket

1. Đăng nhập Cloudflare Dashboard
2. Sidebar → **R2 Object Storage**
3. Click **"Create bucket"**
4. Đặt tên bucket: `truyen-audio` (hoặc tên bạn thích)
5. Click **"Create bucket"**

#### Bước 2: Tạo API Token

1. Vào **R2** → **Manage R2 API Tokens**
2. Click **"Create API Token"**
3. Đặt tên: `TTS Automation`
4. Permissions: **Object Read & Write**
5. Click **"Create API Token"**
6. **LƯU LẠI:**
   - Access Key ID
   - Secret Access Key
   - Endpoint URL (dạng: `https://xxxxx.r2.cloudflarestorage.com`)

#### Bước 3: Cấu hình Public Access (nếu muốn)

1. Vào bucket vừa tạo → **Settings**
2. **Public Access** → **Allow Access**
3. Hoặc kết nối **Custom Domain** để có URL đẹp

**Public URL mẫu:**

- Mặc định: `https://pub-xxxxx.r2.dev`
- Custom domain: `https://audio.yourdomain.com`

---

### B. Supabase (Tùy chọn - để lưu URL audio vào database)

#### Bước 1: Lấy credentials

1. Vào Supabase Dashboard
2. Chọn project của bạn
3. **Settings** → **API**
4. **LƯU LẠI:**
   - **URL:** `https://xxxxx.supabase.co`
   - **anon public key** hoặc **service_role key** (khuyến nghị dùng service_role)

#### Bước 2: Kiểm tra bảng chapter_audios

Đảm bảo bảng `chapter_audios` đã tồn tại với cấu trúc:

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

**Nếu chưa có, tạo bảng bằng SQL Editor trong Supabase.**

---

## Sử dụng phần mềm

### 1. Khởi động

**Cách 1:** Click đúp vào `run.bat`

**Cách 2:** Mở Command Prompt:

```bash
python tts_automation.py
```

### 2. Quy trình 3 bước

#### **📖 Tab 1: Chọn truyện & chương**

**Bước 1:** Chọn truyện từ danh sách bên trái

- Click vào tên truyện muốn xử lý
- Danh sách chương sẽ tự động hiển thị bên phải

**Bước 2:** Chọn chương cần xuất audio

- Click vào chương để chọn (giữ Ctrl để chọn nhiều)
- Hoặc dùng nút **"Chọn tất cả"** để chọn toàn bộ
- Dùng **"Bỏ chọn tất cả"** để reset

**Tips:**

- Nên chia nhỏ batch, mỗi lần xử lý 10-20 chương
- Tránh xử lý quá nhiều chương cùng lúc (tránh bị chặn IP)

---

#### **⚙️ Tab 2: Cấu hình**

##### Cloudflare R2

- ☑️ Tick vào **"Bật upload lên R2"** (nếu muốn upload)
- Điền thông tin từ bước cấu hình ở trên:
  - **Endpoint URL:** `https://xxxxx.r2.cloudflarestorage.com`
  - **Access Key ID:** `xxxxxxxxxxxxxx`
  - **Secret Access Key:** `xxxxxxxxxxxxxx`
  - **Bucket Name:** `truyen-audio`
  - **Public URL:** `https://pub-xxxxx.r2.dev` hoặc custom domain

##### Supabase

- ☑️ Tick vào **"Bật cập nhật Supabase"** (nếu muốn lưu vào DB)
- Điền thông tin:
  - **Supabase URL:** `https://xxxxx.supabase.co`
  - **Supabase Key:** `xxxxxxxxxxxxxx`

##### Rate Limiting

- **Delay giữa các chương:** 3-5 giây (khuyến nghị)
  - Càng cao càng an toàn (tránh bị chặn)
  - Càng thấp càng nhanh (nhưng rủi ro cao hơn)
- **Delay giữa giọng nam/nữ:** 1-2 giây

**Lưu ý:** Cấu hình chỉ cần làm 1 lần, lần sau mở lại sẽ giữ nguyên

---

#### **🚀 Tab 3: Xử lý**

**Bước 1:** Kiểm tra thông tin

- Xem lại truyện đã chọn
- Số lượng chương

**Bước 2:** Nhấn **"🚀 Bắt đầu xử lý"**

**Bước 3:** Theo dõi tiến độ

- **Progress bar:** Hiển thị % hoàn thành
- **Log:** Chi tiết từng bước xử lý
  - ✓ = Thành công
  - ✗ = Lỗi
  - ⚠ = Cảnh báo

**Bước 4:** Chờ đợi

- Phần mềm sẽ tự động:
  1. Tạo audio giọng nam
  2. Tạo audio giọng nữ
  3. Upload lên R2 (nếu bật)
  4. Cập nhật Supabase (nếu bật)
  5. Chuyển sang chương tiếp theo

**Thời gian ước tính:**

- 1 chương: ~30-60 giây (tùy độ dài)
- 10 chương: ~5-10 phút
- 100 chương: ~1-2 giờ

---

### 3. Kiểm tra kết quả

#### File audio local

```
audio_output/
├── Ma_cuon_chieu/
│   ├── Ma_cuon_chieu_chuong_0001_male.mp3
│   ├── Ma_cuon_chieu_chuong_0001_female.mp3
│   ├── Ma_cuon_chieu_chuong_0002_male.mp3
│   └── ...
```

#### Trên Cloudflare R2

1. Vào R2 Dashboard → Bucket của bạn
2. Thư mục: `audio/Tên_Truyện/`
3. Kiểm tra file đã upload

#### Trong Supabase

1. Vào Table Editor → `chapter_audios`
2. Kiểm tra records mới
3. Verify `chapter_id`, `voice`, `audio_url` đúng

---

## Xử lý lỗi

### ❌ "python is not recognized"

**Nguyên nhân:** Python chưa được thêm vào PATH

**Giải pháp:**

1. Gỡ cài đặt Python
2. Cài lại và nhớ tick **"Add Python to PATH"**

---

### ❌ "Module not found: edge_tts"

**Nguyên nhân:** Chưa cài thư viện

**Giải pháp:**

```bash
pip install -r requirements.txt
```

---

### ❌ "Permission denied" khi upload R2

**Nguyên nhân:** API Token không có quyền

**Giải pháp:**

1. Kiểm tra API Token có quyền **Object Read & Write**
2. Tạo lại token mới nếu cần
3. Kiểm tra bucket name đúng chưa

---

### ❌ "Supabase insert failed"

**Nguyên nhân:**

- Service key sai
- RLS policy chặn
- `chapter_id` không tồn tại

**Giải pháp:**

1. Kiểm tra Supabase URL và Key
2. Tắt RLS cho bảng `chapter_audios` (hoặc cấu hình policy phù hợp)
3. Verify `chapter_id` trong JSON có khớp với DB không

---

### ⚠️ Audio không rõ ràng

**Nguyên nhân:** Nội dung chương có ký tự đặc biệt

**Giải pháp:**

- Phần mềm đã tự động làm sạch text
- Nếu vẫn không rõ, kiểm tra log xem text đã được xử lý như thế nào

---

### ⚠️ Lỗi 403 từ Edge-TTS

**Triệu chứng:** `403, message='Invalid response status'`

**Nguyên nhân:**

- Edge-TTS phát hiện quá nhiều request từ IP của bạn
- Có thể do xử lý quá nhanh hoặc quá nhiều chương

**Giải pháp:**

1. **Tăng delay:** Vào Tab 2, tăng delay giữa chương lên 5-10 giây
2. **Chờ đợi:** Dừng xử lý 15-30 phút để IP "nguội" lại
3. **Chia nhỏ batch:** Xử lý 5-10 chương/lần thay vì 20-50 chương
4. **Đổi mạng:** Thử đổi sang mạng khác (4G, VPN) nếu bị chặn lâu
5. **Chạy ban đêm:** Ít người dùng Edge-TTS hơn, ít bị giới hạn hơn

**Lưu ý:** Phần mềm đã tích hợp retry tự động (3 lần), nếu vẫn lỗi thì cần áp dụng các giải pháp trên

---

## Tips & Tricks

### 💡 Tối ưu tốc độ

- Xử lý vào ban đêm (ít người dùng Edge-TTS hơn)
- Chia nhỏ batch: 10-20 chương/lần
- Delay hợp lý: 3 giây giữa chương

### 💡 Tiết kiệm dung lượng

- Chỉ bật upload R2 khi cần
- Xóa file local sau khi upload thành công
- Nén file MP3 nếu cần (dùng tool khác)

### 💡 Bảo mật

- Không share API keys/tokens
- Dùng `.env` file để lưu credentials (đừng commit lên Git)
- Định kỳ rotate API tokens

### 💡 Backup

- Backup file JSON trong `myData/` thường xuyên
- Export database Supabase định kỳ
- Lưu file audio quan trọng ở nhiều nơi

### 💡 Xử lý số lượng lớn

**Ví dụ:** 500 chương

**Cách làm:**

1. Chia thành 25 batch, mỗi batch 20 chương
2. Xử lý mỗi batch, nghỉ 15-30 phút giữa các batch
3. Chạy vào ban đêm, để máy tự động xử lý
4. Kiểm tra log sáng hôm sau

---

## Câu hỏi thường gặp (FAQ)

**Q: Có thể dừng giữa chừng không?**
A: Hiện tại chưa hỗ trợ pause/resume. Nên chia nhỏ batch để dễ quản lý.

**Q: File audio có bị mất chất lượng không?**
A: Edge-TTS cho chất lượng khá tốt, file MP3 đã được tối ưu.

**Q: Có thể chọn giọng đọc khác không?**
A: Hiện tại fix 2 giọng nam/nữ tiếng Việt. Có thể sửa code để thêm giọng khác.

**Q: Upload R2 có tốn phí không?**
A: R2 có 10GB free/tháng. Nếu vượt quá sẽ tính phí.

**Q: Supabase có giới hạn không?**
A: Free plan có giới hạn 500MB database và 2GB bandwidth/tháng.

---

## Liên hệ & Hỗ trợ

Nếu gặp vấn đề:

1. Kiểm tra log trong Tab 3
2. Đọc phần "Xử lý lỗi" ở trên
3. Kiểm tra file JSON có đúng format không
4. Kiểm tra kết nối mạng

---

**Chúc bạn sử dụng thành công! 🎉**
