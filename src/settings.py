from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(".env"))

@lru_cache
def api_key() -> str:
    return os.getenv("CL_API_KEY", "")

@lru_cache
def db_url() -> str:
    return os.getenv("DATABASE_URL", "")
