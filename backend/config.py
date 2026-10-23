from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL     = os.getenv("REDIS_URL")
MODEL_PATH = os.getenv("YOLO_MODEL_PATH") or os.getenv("MODEL_PATH", "weights/best.pt")
UPLOAD_DIR    = "uploads"

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL")  # no default on purpose

