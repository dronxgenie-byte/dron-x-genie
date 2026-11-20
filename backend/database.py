"""
Настройка базы данных для Банка Анисов (SQLite + SQLAlchemy).
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "anis_bank.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Создаёт все таблицы в БД."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Зависимость FastAPI: открывает сессию БД и закрывает после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
