import os
from dotenv import load_dotenv
from google import genai

# 1. Nạp API Key và khởi tạo Client
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 2. Đoạn text chúng ta cần biến thành vector 
# (Trong thực tế, đây chính là node_text hoặc chunk summary)
text_to_embed = "def add(a, b): return a + b"

print(f"Đang tạo Dense Embedding cho chuỗi: '{text_to_embed}' ...\n")

# 3. Gọi API Embedding của Gemini
response = client.models.embed_content(
    model='models/gemini-embedding-001',
    contents=text_to_embed
)

# 4. Lấy mảng vector trả về
vector = response.embeddings[0].values

# In ra xem vector nó có hình thù như thế nào
print(f"-> Đã tạo thành công Vector có độ dài (số chiều): {len(vector)}")
print(f"-> 5 giá trị đầu tiên của Vector: {vector[:5]}")
print("...")