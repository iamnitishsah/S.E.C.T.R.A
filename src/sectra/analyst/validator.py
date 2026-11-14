"""
Check a generated SQL query before it reaches the database.

The query is parsed with sqlglot (MySQL dialect), never matched with regex, and the
query that is executed is the one re-generated from the parse tree, so comments and
anything the parser did not understand cannot reach MySQL.

Rules:
  - exactly one statement, and it is a SELECT (WITH and UNION are allowed)
  - no writes, no SELECT ... INTO, no locking clauses, no user or system variables
  - reads at least one table, only tables from the allowlist, never qualified with a database name
  - only functions the parser recognises (so no SLEEP, BENCHMARK, LOAD_FILE, GET_LOCK), and none
    that describe the server (VERSION, USER, DATABASE)
  - a LIMIT is added, or lowered to max_rows

This is the second line of defence. The first is the read-only MySQL role
(sectra.storage.setup_reader), which holds even if a rule here is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

FORBIDDEN_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
                   exp.TruncateTable, exp.Command, exp.Into, exp.Lock, exp.Set, exp.Use, exp.Transaction,
                   exp.Commit, exp.Rollback, exp.Parameter, exp.SessionParameter, exp.Placeholder)
# Functions sqlglot knows by name that describe the server instead of the data.
FORBIDDEN_FUNCTIONS = {"current_schema", "current_version", "current_user", "current_role", "session_user",
                       "current_catalog", "current_database"}
# Functions sqlglot does not know are rejected (SLEEP, BENCHMARK, LOAD_FILE, GET_LOCK, USER, ...) unless listed here.
EXTRA_FUNCTIONS = {"format", "truncate", "quarter", "if"}


class UnsafeSQL(ValueError):
    """The query broke a rule; the message says which one (it is shown to the model on a retry)."""


@dataclass
class ValidatedQuery:
    sql: str                    # the query to execute: re-generated, comments removed, LIMIT enforced
    tables: list[str]           # allowlisted tables it reads
    limit: int                  # the LIMIT in force


def _check_function(node: exp.Expression) -> None:
    if isinstance(node, exp.Anonymous):
        name = str(node.this).lower()
        if name not in EXTRA_FUNCTIONS:
            raise UnsafeSQL(f"function {name.upper()}() is not allowed")
    elif isinstance(node, exp.Func) and node.sql_name().lower() in FORBIDDEN_FUNCTIONS:
        raise UnsafeSQL(f"function {node.sql_name()}() is not allowed")


def validate(sql: str, allowed_tables: list[str], max_rows: int = 200) -> ValidatedQuery:
    try:
        statements = [s for s in sqlglot.parse(sql, read="mysql") if s is not None]
    except SqlglotError as exc:
        raise UnsafeSQL(f"could not parse the query as MySQL: {str(exc).splitlines()[0]}") from exc
    if len(statements) != 1:
        raise UnsafeSQL(f"expected exactly one statement, found {len(statements)}")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.SetOperation)):
        raise UnsafeSQL(f"only SELECT queries are allowed, not {type(tree).__name__.upper()}")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeSQL(f"{type(node).__name__} is not allowed in a read-only query")
        _check_function(node)

    allowed = {t.lower() for t in allowed_tables}
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    used: set[str] = set()
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if table.db or table.catalog:
            raise UnsafeSQL(f"table names must not be qualified with a database: {table.sql(dialect='mysql')}")
        if name in cte_names:
            continue
        if name not in allowed:
            raise UnsafeSQL(f"table {name!r} is not available; use only: {', '.join(sorted(allowed))}")
        used.add(name)
    if not used:
        raise UnsafeSQL(f"the query must read from one of: {', '.join(sorted(allowed))}")

    limit = max_rows
    current = tree.args.get("limit")
    if current is not None:
        value = current.expression
        if not (isinstance(value, exp.Literal) and value.is_int):
            raise UnsafeSQL("LIMIT must be a plain integer")
        limit = min(int(value.name), max_rows)
    tree = tree.limit(limit)
    return ValidatedQuery(tree.sql(dialect="mysql", comments=False), sorted(used), limit)