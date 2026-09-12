import os
from dotenv import load_dotenv
from google import genai

# loading evironment
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "chuoi_ma_api_cua_ban":
    print("LỖI: Bạn chưa nhập API key thật vào file .env!")
    exit()

# Generate Gemini SDK client
client = genai.Client(api_key=api_key)

print("Đang gửi câu hỏi cho Gemini Pro...")

# 3. Gọi Gemini Pro trả lời thử một câu
response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents='Chào bạn, tôi đang xây dựng hệ thống RAG cho mã nguồn. Bạn có thể nói "Sẵn sàng" nếu bạn nhận được tin nhắn này không?'
)

print("=== GEMINI TRẢ LỜI ===")
print(response.text)