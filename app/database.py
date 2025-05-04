from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Hardcode URL kết nối MySQL (cho mục đích phát triển)
DATABASE_URL = "mysql+pymysql://root:@localhost/coding_platform"

# Tạo engine kết nối
engine = create_engine(DATABASE_URL)

# Tạo session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo base model
Base = declarative_base()

# Dependency để lấy DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()