from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
DATABASE_URL = f"sqlite:///{BASE_DIR / 'prompt_vault.db'}"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "prompts.jsonl"

LOG_DIR.mkdir(exist_ok=True)
