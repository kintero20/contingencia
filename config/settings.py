from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./sbeup.db"
    database_url_sync: str = "sqlite:///./sbeup.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    cors_origins: str = '["*"]'
    upload_dir: str = "uploads"
    static_dir: str = "static"

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
