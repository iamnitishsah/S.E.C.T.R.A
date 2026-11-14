"""One place to build the MySQL connection from .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def get_engine(echo: bool = False, user_env: str = "MYSQL_USER", password_env: str = "MYSQL_PASSWORD") -> Engine:
    url = URL.create(  # URL.create escapes special characters in the password safely
        "mysql+pymysql",
        username=os.environ["user_env"],
        password=os.environ["password_env"],
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.environ["MYSQL_DATABASE"],
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, echo=echo)


def get_reader_engine() -> Engine:
    """Engine for the read-only user (created by sectra.storage.setup_reader); used for generated SQL."""
    import yaml
    cfg = yaml.safe_load(open(ROOT / "configs" / "sql.yaml"))
    return get_engine(user_env=cfg["reader_user_env"], password_env=cfg["reader_password_env"])