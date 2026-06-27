import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Resolve absolute path for database file
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BACKEND_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "research_assistant.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False is required for SQLite in multithreaded environments (like FastAPI)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to yield database sessions to route handlers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
