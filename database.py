# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the database URL (SQLite in this example)
SQLALCHEMY_DATABASE_URL = "sqlite:///./medicare.db"  # SQLite database file will be created in the same directory

# Create the SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the Base class for SQLAlchemy models
Base = declarative_base()

# Function to get a database session (optional)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()