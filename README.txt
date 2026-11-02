# Huy AI — Gemini Edition

Website trợ lý AI giao diện tối, dùng Google Gemini. API key chỉ được đọc ở backend qua biến môi trường.

## Tính năng

- Chat với Gemini và gửi lịch sử hội thoại gần đây.
- Lưu danh sách hội thoại ở localStorage của trình duyệt.
- Đính kèm ảnh JPG/PNG/WEBP để Gemini phân tích.
- Tải PDF có lớp văn bản để trích xuất nội dung rồi hỏi đáp.
- Tạo ảnh bằng model Gemini image (nếu model được bật cho API key/khu vực).
- Tìm kiếm web qua Google Search grounding (nếu model/tài khoản hỗ trợ).
- Nhập giọng nói và đọc câu trả lời bằng Web Speech API của trình duyệt.
- Giới hạn kích thước upload, giới hạn tốc độ API và một số HTTP security headers.

## 1. Tạo Gemini API key

1. Mở https://aistudio.google.com/apikey
2. Đăng nhập Google và tạo API key.
3. Không gửi key cho người khác, không đặt key trong HTML/JavaScript và không commit key lên GitHub.

## 2. Chạy trên máy tính (Windows)

Cần Python 3.10 trở lên.

1. Giải nén ZIP.
2. Mở PowerShell trong thư mục vừa giải nén.
3. Cài thư viện:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Tạo file `.env` bằng cách sao chép `.env.example`.
5. Mở `.env`, thay `GEMINI_API_KEY` bằng key của bạn.
6. Chạy:

   ```powershell
   python backend.py
   ```

7. Mở http://127.0.0.1:5000

macOS/Linux: dùng `python3 -m venv .venv`, `source .venv/bin/activate`, sau đó `python backend.py`.

## 3. Đưa website lên mạng miễn phí bằng GitHub + Render

1. Tạo repository GitHub mới.
2. Upload các file và thư mục ở thư mục dự án vào **thư mục gốc** của repository. Đảm bảo `render.yaml`, `backend.py`, `requirements.txt` nằm ngay ở root.
3. Không upload `.env`. File `.gitignore` đã chặn file này.
4. Đăng nhập https://render.com và kết nối GitHub.
5. Trong Render chọn **New → Blueprint**, chọn repository vừa tạo.
6. Render đọc `render.yaml` và tạo Web Service. Chọn Free nếu được hỏi.
7. Mở dịch vụ vừa tạo → **Environment** → thêm:
   - `GEMINI_API_KEY` = API key lấy từ AI Studio
   - `GEMINI_MODEL` = `gemini-3.8-flash`
   - `GEMINI_IMAGE_MODEL` = `gemini-2.5-flash-image`
8. Nhấn Save/Deploy. Chờ build xong và mở địa chỉ `https://...onrender.com`.
9. Thử mở `https://...onrender.com/api/health`. Nếu `configured` là `true`, backend đã nhận key.

Nếu không dùng Blueprint: tạo **New → Web Service**, chọn repository, Runtime Python, Build Command `pip install -r requirements.txt`, Start Command `gunicorn backend:app`, Plan Free; sau đó thêm biến môi trường như trên.

## 4. Lưu ý về miễn phí và giới hạn

- Render Free có thể spin down sau 15 phút không có truy cập; lần mở tiếp theo có thể mất khoảng một phút. Filesystem miễn phí là tạm thời. Lịch sử hội thoại ở bản này được lưu trong trình duyệt người dùng, không đồng bộ giữa thiết bị.
- Gemini API có hạn mức theo model, khu vực và tài khoản; có thể thay đổi. Kiểm tra Google AI Studio Usage/Billing. Miễn phí không đồng nghĩa không giới hạn.
- Tạo ảnh và Google Search grounding phụ thuộc model/tính năng được cấp cho API key và chính sách giá hiện hành. Nếu model ảnh không hoạt động, xem `GEMINI_IMAGE_MODEL` trong Environment và thông báo lỗi ở log.
- Nhập giọng nói dùng Web Speech API của trình duyệt (thường hoạt động tốt hơn trên Chrome và cần quyền microphone); đọc văn bản dùng SpeechSynthesis. Đây không phải cuộc gọi audio realtime tới Gemini.
- PDF scan chỉ có ảnh, không có lớp văn bản, sẽ không trích xuất được bằng pypdf. Hãy OCR PDF trước hoặc gửi ảnh trang.
- Bản hiện tại giới hạn file đính kèm 10 MB, PDF 35 trang, và API mặc định 30 request/phút/IP. Giới hạn rate-limit lưu trong bộ nhớ, có thể reset khi máy chủ khởi động lại.
- Không dùng gói free cho ứng dụng có dữ liệu nhạy cảm hoặc lượng người dùng lớn. Không nhập mật khẩu, thông tin ngân hàng hoặc dữ liệu riêng tư vào chatbot.

## 5. Cấu hình model

Biến môi trường:
- `GEMINI_API_KEY`: bắt buộc.
- `GEMINI_MODEL`: mặc định `gemini-3.8-flash`.
- `GEMINI_IMAGE_MODEL`: mặc định `gemini-2.5-flash-image`.
- `SYSTEM_INSTRUCTION`: có thể thay đổi hướng dẫn hệ thống.
- `CORS_ORIGINS`: danh sách origin được phép nếu triển khai frontend/backend tách riêng. Khi dùng cùng Render service, không cần chỉnh.

## Cấu trúc dự án

```text
Huy-AI/
├── backend.py
├── requirements.txt
├── render.yaml
├── Procfile
├── .env.example
├── .gitignore
└── static/
    └── index.html
```

## Tài liệu chính thức nên kiểm tra

- Gemini API / tạo nội dung: https://ai.google.dev/api/generate-content
- Google Search grounding: https://ai.google.dev/gemini-api/docs/google-search
- Tạo ảnh Gemini: https://ai.google.dev/gemini-api/docs/image-generation
- Render free limitations: https://render.com/docs/free
