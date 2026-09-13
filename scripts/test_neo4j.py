import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

print("Đang kết nối tới Neo4j Cloud...")

# Khởi tạo Driver kết nối
with GraphDatabase.driver(URI, auth=AUTH) as driver:
    # Kiểm tra kết nối
    driver.verify_connectivity()
    print("-> Đã kết nối Neo4j thành công!\n")
    
    # Mở một session để tương tác với DB
    with driver.session() as session:
        print("Đang xóa data cũ (nếu có) và nạp dữ liệu Đồ thị...")
        
        # Xóa sạch data cũ để test
        session.run("MATCH (n) DETACH DELETE n")
        
        # Tạo 3 hàm và mối quan hệ (Cypher Query Language)
        query = """
        CREATE (f1:Function {name: 'calculate_total'})
        CREATE (f2:Function {name: 'add'})
        CREATE (f3:Function {name: 'multiply'})
        CREATE (f1)-[:CALLS]->(f2)
        CREATE (f1)-[:CALLS]->(f3)
        """
        session.run(query)
        
        # Truy vấn thử
        print("\n=== TEST TRUY VẤN ===")
        result = session.run("MATCH (caller:Function {name: 'calculate_total'})-[:CALLS]->(callee:Function) RETURN callee.name AS callee_name")
        
        print("Hàm 'calculate_total' đang gọi:")
        for record in result:
            print(f"- {record['callee_name']}")