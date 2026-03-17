# 🚀 BẮT ĐẦU NHANH - 5 PHÚT

## ✅ Checklist nhanh

### 1️⃣ Cài đặt (5 phút)
- [ ] Cài Python 3.8+ (nhớ tick "Add to PATH")
- [ ] Click đúp `install.bat` để cài thư viện
- [ ] Đợi cài đặt xong

### 2️⃣ Chạy thử (1 phút)
- [ ] Click đúp `run.bat`
- [ ] Phần mềm mở lên → OK!

### 3️⃣ Sử dụng cơ bản (không cần R2/Supabase)
- [ ] Tab 1: Chọn 1 truyện, chọn 1-2 chương để test
- [ ] Tab 2: KHÔNG tick vào R2 và Supabase (để test local)
- [ ] Tab 3: Nhấn "Bắt đầu xử lý"
- [ ] Đợi 1-2 phút
- [ ] Kiểm tra thư mục `audio_output/` → Có file MP3!

### 4️⃣ Cấu hình đầy đủ (sau khi test thành công)
- [ ] Đọc `HUONG_DAN_SU_DUNG.md` để cấu hình R2 & Supabase
- [ ] Nhập thông tin vào Tab 2
- [ ] Xử lý toàn bộ truyện

---

## 📚 Tài liệu

| File | Mô tả |
|------|-------|
| `INSTALL.md` | Hướng dẫn cài đặt ngắn gọn |
| `HUONG_DAN_SU_DUNG.md` | Hướng dẫn chi tiết đầy đủ |
| `README.md` | Tổng quan dự án (English) |
| `GITHUB_SETUP.md` | Hướng dẫn push lên GitHub |

---

## 🎯 Quy trình đề xuất

### Lần đầu tiên (Test)
1. Chọn 1 truyện ngắn
2. Chọn 2-3 chương đầu
3. KHÔNG bật R2/Supabase
4. Xử lý và kiểm tra file MP3 local
5. Nghe thử audio xem có OK không

### Sau khi test OK
1. Cấu hình R2 (nếu muốn lưu cloud)
2. Cấu hình Supabase (nếu muốn lưu DB)
3. Xử lý từng truyện, mỗi lần 10-20 chương
4. Kiểm tra kết quả sau mỗi batch

### Xử lý số lượng lớn
1. Chia nhỏ: 10-20 chương/batch
2. Delay: 3-5 giây giữa chương
3. Nghỉ: 15-30 phút giữa các batch
4. Chạy ban đêm nếu có nhiều chương

---

## ⚡ Tips nhanh

✅ **Bắt đầu nhỏ:** Test với 2-3 chương trước
✅ **Chia nhỏ batch:** Đừng xử lý quá nhiều cùng lúc
✅ **Kiểm tra thường xuyên:** Xem log và file output
✅ **Backup dữ liệu:** Lưu file JSON trong `myData/`
✅ **Delay hợp lý:** 3-5 giây tránh bị chặn IP

❌ **Tránh:** Xử lý 100+ chương cùng lúc
❌ **Tránh:** Delay quá thấp (< 2 giây)
❌ **Tránh:** Để máy sleep khi đang xử lý

---

## 🆘 Gặp lỗi?

1. Đọc log trong Tab 3
2. Xem phần "Xử lý lỗi" trong `HUONG_DAN_SU_DUNG.md`
3. Kiểm tra:
   - Python đã cài đúng chưa?
   - Thư viện đã cài chưa?
   - File JSON có trong `myData/` chưa?
   - Kết nối mạng OK chưa?

---

## 📊 Kết quả mong đợi

Sau khi xử lý xong, bạn sẽ có:

### Local
```
audio_output/
└── Tên_Truyện/
    ├── Tên_Truyện_chuong_0001_male.mp3
    ├── Tên_Truyện_chuong_0001_female.mp3
    ├── Tên_Truyện_chuong_0002_male.mp3
    └── ...
```

### Cloudflare R2 (nếu bật)
- Thư mục: `audio/Tên_Truyện/`
- File: Giống như local
- URL: `https://your-domain.com/audio/Tên_Truyện/...mp3`

### Supabase (nếu bật)
- Bảng: `chapter_audios`
- Mỗi chương: 2 records (male + female)
- Có đầy đủ: `chapter_id`, `voice`, `audio_url`

---

## 🎉 Chúc mừng!

Bạn đã sẵn sàng chuyển đổi truyện thành audio!

**Bắt đầu ngay:** Click đúp `run.bat`

---

**Cần hỗ trợ thêm?** Đọc `HUONG_DAN_SU_DUNG.md` để biết chi tiết.
