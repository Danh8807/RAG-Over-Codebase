from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Khởi tạo Qdrant chạy local (Lưu data vào thư mục qdrant_storage)
client = QdrantClient(path="qdrant_storage")
collection_name = "codebase_chunks"

# 2. Tạo Collection (Bảng) nếu chưa có
if not client.collection_exists(collection_name):
    print(f"Đang tạo collection '{collection_name}'...")
    client.create_collection(
        collection_name=collection_name,
        # Model của Google trả về mảng 3072 chiều
        vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
    )
else:
    print(f"Collection '{collection_name}' đã tồn tại.")

# 3. Giả lập cái vector bạn vừa lấy được từ file test_embedding.py
# (Ở đây tạo 1 mảng 3072 số giả để test tốc độ lưu)
sample_vector = [-0.0175, -0.0188, 0.0061, -0.0645, -0.0126] + [0.0] * 3067

# 4. Lưu vào Database kèm theo metadata
print("Đang lưu vector vào Qdrant...")
client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=1, 
            vector=sample_vector,
            payload={
                "repo": "RAG-Over-Codebase",
                "path": "src/math.py",
                "symbol": "add",
                "body": "def add(a, b): return a + b",
                "summary": "This function adds two numbers and returns the result."
            }
        )
    ]
)

print("-> Đã lưu thành công! Vector và Meta-data đã nằm an toàn trong DB.")
client.close()