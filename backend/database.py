import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-safe session
Session = scoped_session(SessionLocal)

def get_db():
    """Dependency for getting database session"""
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_session():
    """Simple function to get a new session"""
    return Session()

def close_session():
    """Close the scoped session"""
    Session.remove()