import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Khởi tạo bộ đọc
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

sample_code = b"""
def hello_codebase_rag(name):
    print(f"Hello, {name}!")
    return True

class RAGAgent:
    def __init__(self):
        self.model = "gemini-3.6-flash"
        
    def retrieve(self, query):
        pass
"""

tree = parser.parse(sample_code)
root_node = tree.root_node 

print("=== TRÍCH XUẤT NỘI DUNG CODE TỪ AST ===\n")

# Duyệt qua các node con ở cấp cao nhất
for child in root_node.children:
    # Chỉ lọc lấy các node là hàm hoặc class
    if child.type in ['function_definition', 'class_definition']:
        
        # BÍ QUYẾT: Cắt chuỗi byte ban đầu dựa vào tọa độ của node
        node_bytes = sample_code[child.start_byte:child.end_byte]
        
        # Giải mã từ byte (b"...") sang string bình thường
        node_text = node_bytes.decode('utf-8')
        
        print(f"--- Tìm thấy: {child.type.upper()} (Dòng {child.start_point[0] + 1} -> {child.end_point[0] + 1}) ---")
        print(node_text)
        print("-" * 50 + "\n")