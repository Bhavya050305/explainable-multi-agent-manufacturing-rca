"""
ManuMind AI - Configuration Settings
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in backend/ and project root
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent

backend_env = BACKEND_DIR / ".env"
root_env = BASE_DIR / ".env"

if backend_env.exists():
    load_dotenv(dotenv_path=backend_env, override=True)
if root_env.exists():
    load_dotenv(dotenv_path=root_env, override=False)
else:
    load_dotenv()


class Settings:
    PROJECT_NAME: str = "ManuMind AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/manumind.db")

    # CORS
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
        ).split(",")
        if origin.strip()
    ]

    # LLM & Multi-Agent
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # mock, gemini, openai, anthropic
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CONFIDENCE_ESCALATION_THRESHOLD: float = float(
        os.getenv("CONFIDENCE_ESCALATION_THRESHOLD", "0.6")
    )

    # Paths
    BASE_PATH: Path = BASE_DIR
    MODELS_DIR: Path = BASE_DIR / "ml" / "models_store"
    KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "knowledge_base"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    DEFECT_IMAGES_DIR: Path = BASE_DIR / "data" / "defect_images"

    def get_masked_database_url(self) -> str:
        """Return DATABASE_URL with sensitive password credentials masked."""
        url = self.DATABASE_URL
        if not url:
            return ""
        # Match :password@ pattern
        return re.sub(r":([^/@:]+)@", ":********@", url)


settings = Settings()
