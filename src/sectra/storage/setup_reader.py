"""
Create the read-only MySQL user that the SQL Analyst connects as.

    python -m sectra.storage.setup_reader        (or: make db-role)

Connects as root, creates the user named in .env (MYSQL_READER_USER / MYSQL_READER_PASSWORD),
removes any privileges it had, and grants SELECT on the tables in configs/sql.yaml only.
Safe to re-run: it also resets the password and the grants.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parents[3]
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")           # identifiers cannot be bound as parameters, so check them


def main() -> None:  # pragma: no cover - needs MySQL
    load_dotenv(ROOT / ".env")
    cfg = yaml.safe_load(open(ROOT / "configs" / "sql.yaml"))
    user, password = os.environ[cfg["reader_user_env"]], os.environ[cfg["reader_password_env"]]
    database, tables = os.environ["MYSQL_DATABASE"], cfg["allowed_tables"]
    for name in (user, database, *tables):
        if not NAME_RE.match(name):
            raise SystemExit(f"unsafe name {name!r}: use letters, digits and underscores only")

    root = URL.create("mysql+pymysql", username="root", password=os.environ["MYSQL_ROOT_PASSWORD"],
                      host=os.getenv("MYSQL_HOST", "127.0.0.1"), port=int(os.getenv("MYSQL_PORT", "3306")))
    with create_engine(root).connect() as conn:
        conn.execute(text(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY :pw"), {"pw": password})
        conn.execute(text(f"ALTER USER '{user}'@'%' IDENTIFIED BY :pw"), {"pw": password})
        conn.execute(text(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{user}'@'%'"))
        for table in tables:
            conn.execute(text(f"GRANT SELECT ON `{database}`.`{table}` TO '{user}'@'%'"))
        conn.commit()
        grants = [row[0] for row in conn.execute(text(f"SHOW GRANTS FOR '{user}'@'%'"))]
    print(f"read-only user {user!r}:")
    for g in grants:
        print("  " + g)


if __name__ == "__main__":
    main()