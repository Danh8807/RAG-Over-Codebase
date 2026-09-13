import tantivy
import os
# 1. Định nghĩa Schema (Cấu trúc của các trường văn bản)
# stored=True nghĩa là lưu lại text gốc để có thể in ra sau khi tìm thấy
schema_builder = tantivy.SchemaBuilder()
schema_builder.add_text_field("symbol", stored=True)
schema_builder.add_text_field("body", stored=True)
schema_builder.add_text_field("summary", stored=True)
schema = schema_builder.build()
os.makedirs("tanvity_storage", exist_ok= True)
# 2. Khởi tạo Index (Lưu tạm trên RAM để test)
index = tantivy.Index(schema, path = "tanvity_storage")
writer = index.writer()

print("Đang nạp dữ liệu vào BM25 Index...\n")

# 3. Nạp chunk code mẫu vào hệ thống
writer.add_document(tantivy.Document(
    symbol=["add"],
    body=["def add(a, b): return a + b"],
    summary=["This function adds two numbers and returns the result."]
))
writer.add_document(tantivy.Document(
    symbol=["multiply"],
    body=["def multiply(a, b): return a * b"],
    summary=["This function multiplies two numbers together."]
))

# Chốt (commit) dữ liệu để index bắt đầu tính toán từ khóa
writer.commit()

# 4. Tiến hành truy vấn thử nghiệm
print("=== TEST TÌM KIẾM TỪ KHÓA (BM25) ===")

# Reload để hệ thống nhận diện dữ liệu mới
index.reload()
searcher = index.searcher()

# Tìm kiếm từ "numbers" trên cả 3 trường văn bản
query_text = "numbers"
print(f"Đang tìm từ khóa: '{query_text}' ...")

query = index.parse_query(query_text, ["symbol", "body", "summary"])

# Lấy top 5 kết quả tốt nhất
results = searcher.search(query, 5)

print(f"-> Tìm thấy {len(results.hits)} kết quả!\n")
for score, doc_address in results.hits:
    doc = searcher.doc(doc_address)
    print(f"Điểm BM25: {score:.4f} | Symbol: {doc['symbol'][0]}")
    print(f"Summary: {doc['summary'][0]}")
    print("-" * 40)