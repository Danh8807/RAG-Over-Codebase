import os
from dotenv import load_dotenv
from google import genai
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# 1. Nạp API Key và khởi tạo Gemini Client
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("LỖI: Thiếu API Key!")
    exit()
client = genai.Client(api_key=api_key)

# 2. Khởi tạo bộ đọc AST (Tree-sitter)
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

# 3. Mã nguồn mẫu để test
sample_code = """
def hello_codebase_rag(name):
    print(f"Hello, {name}! Welcome to the system.")
    return True

class RAGAgent:
    def __init__(self):
        self.model = "gemini-3.6-flash"
        
    def retrieve(self, query):
        # Giả lập hành vi tìm kiếm vector
        search_results = ["chunk1", "chunk2"]
        return search_results
""".encode('utf-8')

tree = parser.parse(sample_code)
root_node = tree.root_node

print("=== BẮT ĐẦU TRÍCH XUẤT VÀ TÓM TẮT ===\n")

# 4. Duyệt AST, cắt text và nhờ AI tóm tắt
for child in root_node.children:
    if child.type in ['function_definition', 'class_definition']:
        
        # Cắt mã nguồn
        node_bytes = sample_code[child.start_byte:child.end_byte]
        node_text = node_bytes.decode('utf-8')
        
        print(f"[*] Đang đọc {child.type} (Dòng {child.start_point[0] + 1} -> {child.end_point[0] + 1})...")
        
        # Tạo Prompt theo đúng yêu cầu khắt khe của Capstone project
        prompt_text = (
            "Summarize this code in one sentence, naming its public contract and side effects. "
            "Return ONLY the summary sentence.\n\n"
            f"Code:\n{node_text}"
        )
        
        # Gửi cho Gemini 3.6 Flash
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_text
        )
        
        print(f"-> CHUNK SUMMARY: {response.text.strip()}\n")
        print("-" * 60 + "\n")