"""Global sozlamalar (.env faylidan o'qiladi)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"          # barcha bazalar shu papkada saqlanadi
DATA_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()]

DEFAULT_ROOTER_CMD = os.getenv("ROOTER_CMD", "rooter").strip().lstrip("/").lower() or "rooter"
DEFAULT_ROOTER_PIN = os.getenv("ROOTER_PIN", "9767").strip() or "9767"

PAGE_SIZE = 8                                   # ro'yxatlardagi elementlar soni
RESERVED_CMDS = {"start", "help", "admin", "cancel"}   # yashirin buyruq nomi sifatida ruxsat etilmaydi
