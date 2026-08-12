# config.py
import os
from pathlib import Path

def _get_gemini_key():
    # En Vercel no hay .env; la clave debe estar en Project Settings > Environment Variables
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if key:
        return key
    # Local: cargar desde .env
    if os.environ.get("VERCEL") != "1":
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parent / ".env")
            key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        except Exception:
            pass
    return (os.environ.get("GEMINI_API_KEY") or "").strip()

class Config:
    GEMINI_API_KEY = _get_gemini_key()
