# Hướng dẫn đẩy code lên GitHub

## Bước 1: Tạo repository trên GitHub

1. Truy cập: https://github.com/new
2. Điền thông tin:
   - **Repository name:** `tts-automation` (hoặc tên bạn muốn)
   - **Description:** "TTS Automation Tool - Chuyển đổi truyện thành audio tự động"
   - **Visibility:** Private hoặc Public (tùy bạn)
   - **KHÔNG** tick vào "Add a README file" (vì đã có rồi)
3. Click **Create repository**

## Bước 2: Kết nối với GitHub

Sau khi tạo repository, GitHub sẽ hiển thị hướng dẫn. Bạn làm theo cách này:

### Mở Command Prompt tại thư mục dự án, chạy lần lượt:

```bash
# Thêm remote repository (thay YOUR_USERNAME và REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Đổi tên branch thành main (nếu cần)
git branch -M main

# Push code lên GitHub
git push -u origin main
```

**Ví dụ cụ thể:**
```bash
git remote add origin https://github.com/johndoe/tts-automation.git
git branch -M main
git push -u origin main
```

## Bước 3: Xác thực

Khi push lần đầu, GitHub sẽ yêu cầu đăng nhập:
- **Username:** Tên GitHub của bạn
- **Password:** Sử dụng **Personal Access Token** (không phải mật khẩu)

### Tạo Personal Access Token:
1. Vào GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click **Generate new token (classic)**
3. Chọn quyền: `repo` (full control)
4. Click **Generate token**
5. **Copy token** và lưu lại (chỉ hiển thị 1 lần)
6. Dùng token này làm password khi push

## Xong!

Code của bạn đã được đẩy lên GitHub. Bạn có thể xem tại:
`https://github.com/YOUR_USERNAME/REPO_NAME`

---

## Lưu ý

✅ Thư mục `myData/` đã được loại trừ (trong `.gitignore`)
✅ File `.env` cũng được loại trừ (bảo mật)
✅ Chỉ có source code và tài liệu được push lên

## Các lệnh Git hữu ích

```bash
# Kiểm tra trạng thái
git status

# Thêm file mới
git add .

# Commit thay đổi
git commit -m "Mô tả thay đổi"

# Push lên GitHub
git push

# Pull code mới nhất
git pull

# Xem lịch sử commit
git log --oneline
```
