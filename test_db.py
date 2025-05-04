import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def test_connection():
    # Load biến môi trường
    load_dotenv()
    
    # Lấy URL kết nối
    database_url = os.getenv("DATABASE_URL")
    print(f"Đang thử kết nối tới: {database_url}")
    
    try:
        # Tạo engine kết nối
        engine = create_engine(database_url)
        
        # Thử kết nối và thực hiện truy vấn đơn giản
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Kết nối thành công!")
            
            # Kiểm tra database cụ thể
            result = connection.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"Các bảng trong database: {tables}")
            
            # Kiểm tra dữ liệu trong bảng users
            result = connection.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"Số lượng users trong database: {user_count}")
            
        return True
    except Exception as e:
        print(f"Lỗi kết nối: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()