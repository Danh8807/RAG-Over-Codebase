import os
import glob
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import tantivy
from neo4j import GraphDatabase
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
import tree_sitter_python as tspy
from tree_sitter import Language, Parser

# ==========================================
# 1. KHỞI TẠO KẾT NỐI & CÔNG CỤ
# ==========================================
load_dotenv()

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

qdrant = QdrantClient(path="qdrant_storage")
COLLECTION_NAME = "codebase_chunks"
if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
    )

schema_builder = tantivy.SchemaBuilder()
schema_builder.add_text_field("symbol", stored=True)
schema_builder.add_text_field("body", stored=True)
schema_builder.add_text_field("summary", stored=True)
os.makedirs("tantivy_storage", exist_ok=True)
tantivy_index = tantivy.Index(schema_builder.build(), path="tantivy_storage")
tantivy_writer = tantivy_index.writer()

neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"), 
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# Khởi tạo Tree-sitter cho Python
PY_LANGUAGE = Language(tspy.language())
parser = Parser(PY_LANGUAGE)

# ==========================================
# 2. HÀM CẮT AST BẰNG TREE-SITTER
# ==========================================
def extract_ast_chunks(file_path):
    """Đọc file Python, trích xuất các hàm và luồng gọi hàm bên trong."""
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    
    tree = parser.parse(bytes(source_code, "utf8"))
    chunks = []
    
    # Duyệt qua các node cấp 1 để tìm khai báo hàm (function_definition)
    for node in tree.root_node.children:
        if node.type == 'function_definition':
            symbol_name = ""
            # Tìm tên hàm
            for child in node.children:
                if child.type == 'identifier':
                    symbol_name = source_code[child.start_byte:child.end_byte]
                    break
            
            code_body = source_code[node.start_byte:node.end_byte]
            
            # Tìm các hàm bị gọi bên trong thân hàm này (Call Graph)
            called_symbols = []
            def traverse(n):
                if n.type == 'call':
                    for c in n.children:
                        if c.type == 'identifier':
                            called_symbols.append(source_code[c.start_byte:c.end_byte])
                for c in n.children:
                    traverse(c)
            traverse(node)
            
            chunks.append({
                "symbol_name": symbol_name,
                "code_body": code_body,
                "called_symbols": list(set(called_symbols))
            })
    return chunks

# ==========================================
# 3. HÀM XỬ LÝ CỐT LÕI (CÓ RETRY)
# ==========================================
@retry(
    wait=wait_random_exponential(multiplier=1, max=60), 
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def process_chunk(repo_name, file_path, symbol_name, code_body, called_symbols):
    print(f"\n🚀 Đang xử lý hàm: '{symbol_name}'...")
    
    print("   -> Đang nhờ Gemini tóm tắt...")
    prompt = f"Summarize this Python function in 1-2 sentences:\n\n{code_body}"
    summary_response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt
    )
    summary_text = summary_response.text.strip()

    print("   -> Đang tạo Vector Embedding...")
    embed_response = ai_client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=f"{symbol_name}: {summary_text}" 
    )
    vector = embed_response.embeddings[0].values

    point_id = hash(f"{file_path}_{symbol_name}") & 0xFFFFFFFFFFFFFFFF 
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(
            id=point_id, 
            vector=vector, 
            payload={"repo": repo_name, "path": file_path, "symbol": symbol_name, "body": code_body, "summary": summary_text}
        )]
    )
    print("   -> [OK] Đã lưu vào Qdrant")

    tantivy_writer.add_document(tantivy.Document(
        symbol=[symbol_name],
        body=[code_body],
        summary=[summary_text]
    ))
    print("   -> [OK] Đã lưu vào Tantivy")

    with neo4j_driver.session() as session:
        session.run("MERGE (f:Function {name: $name, path: $path})", name=symbol_name, path=file_path)
        for callee in called_symbols:
            session.run("""
                MERGE (caller:Function {name: $caller_name})
                MERGE (callee:Function {name: $callee_name})
                MERGE (caller)-[:CALLS]->(callee)
            """, caller_name=symbol_name, callee_name=callee)
    print("   -> [OK] Đã lưu đồ thị vào Neo4j")

def finish_ingestion():
    tantivy_writer.commit()
    neo4j_driver.close()
    qdrant.close()
    print("\n✅ HOÀN TẤT INGESTION PIPELINE! Dữ liệu đã an toàn.")

# ==========================================
# 4. CHẠY THỰC TẾ (QUÉT THƯ MỤC)
# ==========================================
if __name__ == "__main__":
    import time
    try:
        repo_name = "RAG-Over-Codebase"
        # Quét tìm tất cả các file .py trong thư mục src
        target_files = glob.glob("src/**/*.py", recursive=True)
        
        print(f"🔍 Tìm thấy {len(target_files)} file Python cần xử lý.")
        
        for file_path in target_files:
            print(f"\n📂 Bắt đầu phân tích file: {file_path}")
            # Tree-sitter chặt file ra thành các hàm
            chunks = extract_ast_chunks(file_path)
            
            # Đẩy từng hàm vào dây chuyền Database
            for chunk in chunks:
                process_chunk(
                    repo_name=repo_name,
                    file_path=file_path,
                    symbol_name=chunk["symbol_name"],
                    code_body=chunk["code_body"],
                    called_symbols=chunk["called_symbols"]
                )
                time.sleep(2)  # Giảm tốc độ để tránh quá tải API
    except Exception as e:
        print(f"\n❌ Lỗi nghiêm trọng: {e}")
    finally:
        finish_ingestion() 