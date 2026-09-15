import os
from google import genai
import retriever 
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Bọc áo giáp Retry: Thử lại tối đa 5 lần nếu API lỗi
@retry(
    wait=wait_random_exponential(multiplier=1, max=60), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def ask_gemini_with_retry(prompt):
    return ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )

def generate_answer(user_query):
    print("\n🚀 KÍCH HOẠT GIAI ĐOẠN 3: GENERATION...")
    
    # 1. Kéo dữ liệu từ 3 Database
    context_data = retriever.search_codebase(user_query)
    
    if not context_data.strip():
        print("❌ Không tìm thấy thông tin nào trong Codebase để trả lời.")
        return

    print("🧠 ĐANG NHỜ GEMINI SUY LUẬN TỪ NGỮ CẢNH (Auto-Retry nếu mạng lag)...")
    
    # 2. Lắp ráp Prompt
    prompt = f"""Bạn là một Chuyên gia Kỹ sư Hệ thống AI (AI System Engineer). 
Nhiệm vụ của bạn là giải thích mã nguồn (Codebase) cho lập trình viên.
Dựa vào các Ngữ cảnh (Context) được trích xuất từ Cơ sở dữ liệu dưới đây, hãy trả lời câu hỏi của người dùng. 

[NGỮ CẢNH TỪ CƠ SỞ DỮ LIỆU]
{context_data}

[CÂU HỎI CỦA NGƯỜI DÙNG]
{user_query}

[YÊU CẦU BẮT BUỘC]
- Trả lời rõ ràng, chia thành các gạch đầu dòng.
- Nếu ngữ cảnh có đồ thị luồng gọi hàm (Dependencies), BẮT BUỘC phải giải thích logic đó.
- TUYỆT ĐỐI không bịa đặt thông tin nếu không có trong ngữ cảnh. Trả lời bằng tiếng Việt.
"""

    # 3. Gửi Prompt qua hàm đã bọc Retry
    try:
        response = ask_gemini_with_retry(prompt)
        
        print("\n" + "🔥 "*20)
        print("🤖 TRỢ LÝ AI TRẢ LỜI:")
        print("🔥 "*20)
        print(response.text)
        print("🔥 "*20 + "\n")
    except Exception as e:
        print(f"\n❌ Đã thử lại nhiều lần nhưng Server Google vẫn sập. Lỗi: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 CHÀO MỪNG ĐẾN VỚI HỆ THỐNG RAG-OVER-CODEBASE!")
    print("Hệ thống đã sẵn sàng. Gõ 'exit' hoặc 'quit' để thoát.")
    print("="*60)
    
    try:
        while True:
            user_input = input("\n👤 BẠN: ")
            
            if user_input.strip().lower() in ['exit', 'quit']:
                print("\n👋 Đang đóng hệ thống... Tạm biệt!")
                break
                
            if not user_input.strip():
                continue
                
            generate_answer(user_input)
            
    finally:
        retriever.qdrant.close()
        retriever.neo4j_driver.close()