from sqlalchemy import create_engine
from pathlib import Path
from dotenv import load_dotenv
import os

# load .env from project root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL") or \
               "postgresql+psycopg2://postgres:postgres@localhost:5432/court_outcomes"

def get_engine():
    """Return a SQLAlchemy Engine using DATABASE_URL."""
    return create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
