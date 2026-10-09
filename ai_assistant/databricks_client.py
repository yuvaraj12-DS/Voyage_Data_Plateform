"""Small, read-only query wrapper for the Databricks SQL Connector."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from databricks import sql

from .config import (
    DATABRICKS_HTTP_PATH,
    DATABRICKS_SERVER_HOSTNAME,
    DATABRICKS_TOKEN,
)


class DataAccessError(RuntimeError):
    """Raised when a trusted analytical query fails."""


def _normalise_hostname(hostname: str) -> str:
    return hostname.removeprefix("https://").removeprefix("http://").strip("/")


def get_db_connection():
    missing = [
        name
        for name, value in (
            ("DATABRICKS_SERVER_HOSTNAME", DATABRICKS_SERVER_HOSTNAME),
            ("DATABRICKS_HTTP_PATH", DATABRICKS_HTTP_PATH),
            ("DATABRICKS_TOKEN", DATABRICKS_TOKEN),
        )
        if not value
    ]
    if missing:
        raise DataAccessError("Databricks configuration is incomplete: " + ", ".join(missing))

    try:
        return sql.connect(
            server_hostname=_normalise_hostname(DATABRICKS_SERVER_HOSTNAME),
            http_path=DATABRICKS_HTTP_PATH,
            access_token=DATABRICKS_TOKEN,
        )
    except Exception as exc:
        # Do not propagate raw connector details to the LLM or end user.
        raise DataAccessError("Could not establish a Databricks SQL connection.") from exc


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        # Connector returns DECIMAL for currency; float is convenient for model/UI output.
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def fetch_all(query: str, parameters: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """Execute a fixed, parameterized SELECT and return rows as JSON-friendly dicts.

    Use `?` placeholders and a positional parameter sequence. SQL identifiers must
    come from config.table_name(), never from the user's natural-language question.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(query, list(parameters))
        else:
            cursor.execute(query)
        column_names = [column[0] for column in (cursor.description or [])]
        result = []
        for row in cursor.fetchall():
            result.append({
                column_names[index]: _json_value(row[index])
                for index in range(len(column_names))
            })
        return result
    except DataAccessError:
        raise
    except Exception as exc:
        raise DataAccessError("The approved Databricks query could not be completed.") from exc
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def fetch_one(query: str, parameters: Sequence[Any] | None = None) -> dict[str, Any]:
    rows = fetch_all(query, parameters)
    return rows[0] if rows else {}
