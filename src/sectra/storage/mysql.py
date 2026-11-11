"""One place to build the MySQL connection from .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def get_engine(echo: bool = False) -> Engine:
    url = URL.create(  # URL.create escapes special characters in the password safely
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.environ["MYSQL_DATABASE"],
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, echo=echo)