import os
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
import tantivy
from neo4j import GraphDatabase

# ==========================================
# 1. KHỞI TẠO KẾT NỐI (READ-ONLY)
# ==========================================
load_dotenv()
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

qdrant = QdrantClient(path="qdrant_storage")
COLLECTION_NAME = "codebase_chunks"

tantivy_index = tantivy.Index.open("tantivy_storage")
searcher = tantivy_index.searcher()

# KẾT NỐI NEO4J CLOUD
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"), 
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# ==========================================
# 2. CÁC HÀM BỔ TRỢ
# ==========================================
def reciprocal_rank_fusion(vector_results, keyword_results, k=60):
    rrf_scores = {}
    
    for rank, res in enumerate(vector_results):
        symbol = res.payload['symbol']
        rrf_scores[symbol] = {
            "score": 1.0 / (rank + k), 
            "payload": res.payload,
            "found_in": "Qdrant"
        }
        
    for rank, (score, doc_address) in enumerate(keyword_results):
        doc = searcher.doc(doc_address)
        symbol = doc['symbol'][0]
        
        rrf_score = 1.0 / (rank + k)
        if symbol in rrf_scores:
            rrf_scores[symbol]["score"] += rrf_score
            rrf_scores[symbol]["found_in"] = "Both (Qdrant + Tantivy)"
        else:
            rrf_scores[symbol] = {
                "score": rrf_score,
                "payload": {"symbol": symbol, "summary": doc['summary'][0], "path": "N/A"},
                "found_in": "Tantivy"
            }
            
    sorted_results = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results

def get_function_dependencies(symbol_name):
    """Truy vấn Neo4j để xem hàm này có gọi các hàm nào khác không."""
    query = """
    MATCH (caller:Function {name: $name})-[:CALLS]->(callee:Function)
    RETURN DISTINCT callee.name AS callee_name
    """
    with neo4j_driver.session() as session:
        result = session.run(query, name=symbol_name)
        return [record["callee_name"] for record in result]

# ==========================================
# 3. HÀM TÌM KIẾM CHÍNH (ĐỘNG CƠ FULL-STACK)
# ==========================================
def search_codebase(user_query):
    print(f"\n🔍 ĐANG TÌM KIẾM: '{user_query}'")
    print("="*70)

    # A. Semantic Search
    embed_response = ai_client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=user_query
    )
    vector_results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=embed_response.embeddings[0].values,
        limit=3 
    ).points

    # B. Keyword Search
    tantivy_query = tantivy_index.parse_query(user_query, ["symbol", "body", "summary"])
    keyword_results = searcher.search(tantivy_query, 3).hits

    # C. Reranking (Hợp nhất kết quả)
    final_results = reciprocal_rank_fusion(vector_results, keyword_results)

    print("🏆 KẾT QUẢ RERANKING VÀ ĐỒ THỊ (FULL CONTEXT):")
    # Chỉ lấy Top 2 kết quả tốt nhất để phân tích sâu
    context_text = ""
    for i, res in enumerate(final_results[:2], 1):
        payload = res['payload']
        symbol_name = payload['symbol']
        # D. KÉO NGỮ CẢNH ĐỒ THỊ TỪ NEO4J
        dependencies = get_function_dependencies(symbol_name)
        deps_str = ', '.join(dependencies) if dependencies else 'Không có'
        
        # Vẫn in ra Terminal cho bạn xem như cũ
        print(f" {i}. Hàm: [{symbol_name}] - File: {payload.get('path', 'N/A')}")
        print(f"    - Tìm thấy bởi: {res['found_in']} (Điểm: {res['score']:.4f})")
        print(f"    - Tóm tắt:      {payload['summary']}")
        print(f"    🔗 [Neo4j Graph] Phụ thuộc: {deps_str}\n")
        
        # 2. Đóng gói dữ liệu vào chuỗi Context
        context_text += f"Hàm: {symbol_name}\nFile: {payload.get('path', 'N/A')}\nTóm tắt: {payload['summary']}\nCác hàm được gọi bên trong: {deps_str}\n\n"
        
    # 3. Trả về toàn bộ chuỗi để generator.py sử dụng
    return context_text

# ==========================================
# 4. CHẠY THỬ
# ==========================================
if __name__ == "__main__":
    try:
        search_codebase("calculate the total sum and product")
    finally:
        # Đóng Database an toàn
        qdrant.close()
        neo4j_driver.close()