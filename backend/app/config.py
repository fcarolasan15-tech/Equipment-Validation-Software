from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "DMPI Equipment Validation Software"
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    database_url: str = "sqlite:///./evs.db"

    vault_root: Path = Path("../templates")
    storage_root: Path = Path("../storage")

    libreoffice_bin: str = "soffice"
    pdf_render_dpi: int = 200
    visual_diff_threshold: float = 0.02

    company_name: str = "Del Monte Philippines Inc."
    company_short: str = "DMPI"

    class Config:
        env_file = ".env"


settings = Settings()
