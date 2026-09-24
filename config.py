import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "hackathon-development-key")
    DATABASE_PATH = BASE_DIR / "database" / "landslide.db"
    DATA_DIR = BASE_DIR / "data"
    MODEL_PATH = BASE_DIR / "ml" / "model.pkl"
    DEMO_MODE = os.getenv("DEMO_MODE", "1") == "1"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    RISK_THRESHOLDS = {"low": 30, "moderate": 50, "high": 70, "critical": 100}
