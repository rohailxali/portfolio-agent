import os
import json
from pathlib import Path
from typing import Optional

import keyring
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "portfolio-agent"
CONFIG_DIR = Path.home() / ".portfolio-agent"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = os.getenv("PORTFOLIO_API_URL", "http://localhost:8000/api/v1")


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        return {"api_url": DEFAULT_API_URL}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {"api_url": DEFAULT_API_URL}


def save_config(data: dict) -> None:
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_api_url() -> str:
    return load_config().get("api_url", DEFAULT_API_URL)


def set_api_url(url: str) -> None:
    cfg = load_config()
    cfg["api_url"] = url.rstrip("/")
    save_config(cfg)


def save_token(token: str) -> None:
    keyring.set_password(APP_NAME, "access_token", token)


def get_token() -> Optional[str]:
    return keyring.get_password(APP_NAME, "access_token")


def clear_token() -> None:
    try:
        keyring.delete_password(APP_NAME, "access_token")
    except keyring.errors.PasswordDeleteError:
        pass