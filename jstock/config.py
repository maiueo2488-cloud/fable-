"""環境変数(.env)からの設定読み込み。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    jquants_api_key: str | None
    discord_webhook_url: str | None
    shikiho_data_path: Path


def load_config(env_path: Path | None = None) -> Config:
    load_dotenv(dotenv_path=env_path, override=False)
    return Config(
        jquants_api_key=os.getenv("JQUANTS_API_KEY") or None,
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
        shikiho_data_path=Path(os.getenv("SHIKIHO_DATA_PATH", "./data/shikiho/latest.csv")),
    )
