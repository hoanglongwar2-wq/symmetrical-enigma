import os, base64, binascii, logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from io import BytesIO

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
limiter = Limiter(get_remote_address, app=app, default_limits=["30 per minute"], storage_uri="memory://")
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
CHAT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
client = genai.Client(api_key=API_KEY) if API_KEY else None
SYSTEM = os.getenv("SYSTEM_INSTRUCTION",
    "Bạn là Huy AI, trợ lý tiếng Việt thông minh, thân thiện và chính xác. "
    "Trả lời có cấu trúc, giải thích dễ hiểu, đưa ví dụ khi hữu ích. "
    "Nếu thiếu dữ kiện hoặc không chắc chắn, hãy nói rõ. Không bịa nguồn.")

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    return response

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "Huy AI", "model": CHAT_MODEL,
                    "configured": bool(client)})

def require_client():
    if client is None:
        return jsonify({"error": "Máy chủ chưa có GEMINI_API_KEY. Hãy thêm API key trong Environment."}), 503
    return None

def decode_attachment(att):
    if not isinstance(att, dict) or not att.get("data"):
        return None, None, None
    mime = str(att.get("mimeType", ""))
    if mime not in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
        raise ValueError("Chỉ hỗ trợ ảnh JPG, PNG, WEBP và PDF.")
    try:
        raw = base64.b64decode(att["data"], validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Dữ liệu tệp đính kèm không hợp lệ.")
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("Tệp tối đa 10 MB.")
    name = str(att.get("name", "attachment"))[:120]
    return mime, raw, name

@app.post("/api/chat")
def chat():
    err = require_client()
    if err: return err
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message: return jsonify({"error": "Bạn chưa nhập nội dung."}), 400
    if len(message) > 18000: return jsonify({"error": "Tin nhắn quá dài (tối đa 18.000 ký tự)."}), 413

    contents = []
    history = data.get("history", [])
    if isinstance(history, list):
        for item in history[-16:]:
            if not isinstance(item, dict): continue
            role = "user" if item.get("role") == "user" else "model"
            txt = str(item.get("content", "")).strip()
            if txt: contents.append(types.Content(role=role, parts=[types.Part(text=txt[:10000])]))

    parts = [types.Part(text=message)]
    try:
        mime, raw, name = decode_attachment(data.get("attachment"))
        if mime and mime.startswith("image/"):
            parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=raw)))
            parts.append(types.Part(text="Hãy quan sát và phân tích hình ảnh đính kèm."))
        elif mime == "application/pdf":
            reader = PdfReader(BytesIO(raw))
            if len(reader.pages) > 35:
                return jsonify({"error": "PDF tối đa 35 trang trong một lần hỏi."}), 413
            extracted = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            if not extracted.strip():
                return jsonify({"error": "Không trích xuất được chữ trong PDF. Có thể đây là PDF scan; hãy gửi ảnh trang hoặc PDF có OCR."}), 422
            parts.append(types.Part(text="Nội dung trích xuất từ PDF ("+name+"):\n"+extracted[:90000]))
        contents.append(types.Content(role="user", parts=parts))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM, temperature=0.65, max_output_tokens=5000)
        if data.get("googleSearch") is True:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]
        response = client.models.generate_content(model=CHAT_MODEL, contents=contents, config=config)
        return jsonify({"reply": response.text or "Gemini chưa trả về nội dung.", "model": CHAT_MODEL})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logging.exception("Gemini chat failed")
        msg = str(exc).lower()
        if any(x in msg for x in ("quota", "429", "resource_exhausted")):
            return jsonify({"error": "Đã chạm hạn mức Gemini. Hãy kiểm tra AI Studio > Usage và thử lại sau."}), 429
        if any(x in msg for x in ("api key", "unauthorized", "permission_denied", "401")):
            return jsonify({"error": "Gemini API key không hợp lệ hoặc chưa được cấp quyền."}), 401
        if data.get("googleSearch") is True and ("google_search" in msg or "tool" in msg):
            return jsonify({"error": "Model hoặc tài khoản hiện chưa hỗ trợ Google Search grounding. Hãy tắt nút Tìm web hoặc đổi model."}), 502
        return jsonify({"error": "Gemini gặp lỗi. Kiểm tra log máy chủ hoặc thử lại sau."}), 502

@app.post("/api/image")
def image():
    err = require_client()
    if err: return err
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    if not prompt: return jsonify({"error": "Hãy nhập mô tả ảnh."}), 400
    if len(prompt) > 3000: return jsonify({"error": "Mô tả ảnh tối đa 3.000 ký tự."}), 413
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]))
        for part in (response.candidates[0].content.parts if response.candidates else []):
            if getattr(part, "inline_data", None):
                blob = part.inline_data
                return jsonify({"image": base64.b64encode(blob.data).decode("ascii"),
                                "mimeType": blob.mime_type or "image/png"})
        return jsonify({"error": "Model không trả về ảnh. Kiểm tra model tạo ảnh và quyền API."}), 502
    except Exception:
        logging.exception("Gemini image generation failed")
        return jsonify({"error": "Không tạo được ảnh. Model tạo ảnh có thể chưa khả dụng hoặc cần bật thanh toán/hạn mức."}), 502

@app.errorhandler(429)
def rate_limited(_):
    return jsonify({"error": "Bạn gửi quá nhanh. Vui lòng đợi một phút rồi thử lại."}), 429

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Yêu cầu quá lớn. Giới hạn tải lên của máy chủ là 15 MB."}), 413

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
