from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# 获取 backend 目录路径
BACKEND_DIR = Path(__file__).parent.parent
DATABASE_PATH = BACKEND_DIR / "hedge_fund.db"

# 数据库配置 - 使用绝对路径
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 创建 SQLAlchemy 引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 需要此配置
)

# 创建 SessionLocal 类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建模型的 Base 类
Base = declarative_base()

# FastAPI 的依赖注入函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 