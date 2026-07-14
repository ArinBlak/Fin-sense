from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

# Fall back to a local SQLite file when POSTGRES_DB_URL is not configured.
# This lets developers run the backend with zero extra infrastructure.
DATABASE_URL = os.getenv("POSTGRES_DB_URL", "sqlite:///./finsense.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite requires check_same_thread=False because FastAPI uses a thread-pool
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
