import bcrypt
from sqlalchemy import create_engine, text

# Kết nối đến database
engine = create_engine("mysql+pymysql://root:@localhost/coding_platform")

# Cập nhật mật khẩu admin
def reset_admin_password():
    # Tạo hash mới cho mật khẩu "admin123"
    password = "admin123"
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    hashed_str = hashed.decode('utf-8')
    
    print(f"New hashed password: {hashed_str}")
    
    # Cập nhật vào database
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET hashed_password = :hashed WHERE username = 'admin'"),
            {"hashed": hashed_str}
        )
        conn.commit()
        print(f"Admin password updated successfully. Rows affected: {result.rowcount}")

if __name__ == "__main__":
    reset_admin_password()