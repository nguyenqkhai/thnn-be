import bcrypt
from sqlalchemy import create_engine, text
import sys

# Kết nối đến database
engine = create_engine("mysql+pymysql://root:@localhost/coding_platform")

# Kiểm tra thông tin đăng nhập
def check_auth():
    with engine.connect() as conn:
        # Truy vấn thông tin người dùng
        result = conn.execute(text("SELECT id, username, hashed_password FROM users WHERE username = 'admin'"))
        user = result.fetchone()
        
        if not user:
            print("User 'admin' not found in database!")
            return
        
        user_id, username, hashed_password = user
        print(f"User found: {username}, ID: {user_id}")
        print(f"Stored hashed password: {hashed_password}")
        
        # Kiểm tra password
        password = "admin123"
        password_bytes = password.encode('utf-8')
        
        try:
            # In ra giá trị hashed_password
            print(f"Hashed password type: {type(hashed_password)}")
            if isinstance(hashed_password, str):
                hashed_bytes = hashed_password.encode('utf-8')
            else:
                hashed_bytes = hashed_password
                
            # Thử xác minh mật khẩu
            is_valid = bcrypt.checkpw(password_bytes, hashed_bytes)
            print(f"Password verification result: {is_valid}")
        except Exception as e:
            print(f"Error checking password: {str(e)}")
            
        # Thử tạo hash mới từ password để kiểm tra format
        try:
            new_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            print(f"New hash for 'admin123': {new_hash}")
        except Exception as e:
            print(f"Error creating new hash: {str(e)}")

if __name__ == "__main__":
    check_auth()