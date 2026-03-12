from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'prompt_vault.db'}"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "prompts.jsonl"

LOG_DIR.mkdir(exist_ok=True)
