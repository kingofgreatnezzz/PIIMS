"""
db.py
=====
Database access layer for the
POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS)
Nigeria Police Force - Oji-River Area Command, Enugu State.

The module wraps Python's built-in ``sqlite3`` driver and exposes a very small
API that the Streamlit front-end (``app.py``) can call:

    get_connection()              -> raw sqlite3.Connection
    execute_query(query, params)  -> INSERT/UPDATE/DELETE helper (auto-commit)
    fetch_all(query, params)      -> list[sqlite3.Row]
    fetch_one(query, params)      -> sqlite3.Row | None

Design notes
------------
* A brand new connection is opened for every call.  Streamlit re-runs the whole
  script from top to bottom on every widget interaction and does so on a worker
  thread, so short-lived connections avoid any cross-thread sharing problems.
* ``PRAGMA foreign_keys = ON`` is issued on every connection.  SQLite disables
  foreign-key enforcement by default, and it is a *per-connection* setting.
* Table/column names used in dynamic SQL always come from the module-level
  constants below (never from user input) and are additionally validated by
  ``validate_identifier()``.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterable, Optional, Sequence

# --------------------------------------------------------------------------- #
#  Paths
# --------------------------------------------------------------------------- #
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DB_PATH: str = os.path.join(BASE_DIR, "police_ims.db")
PHOTOS_DIR: str = os.path.join(BASE_DIR, "photos")

# --------------------------------------------------------------------------- #
#  Schema - exactly as specified in the project document
# --------------------------------------------------------------------------- #
SCHEMA_SQL: str = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK(role IN ('Admin', 'Viewer')),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS officers (
    officer_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    officer_number TEXT    UNIQUE NOT NULL,
    name           TEXT    NOT NULL,
    rank           TEXT    NOT NULL,
    department     TEXT    NOT NULL CHECK(department IN
                     ('Intelligence', 'Crime Investigation', 'Fraud Investigation')),
    date_joined    DATE    NOT NULL
);

CREATE TABLE IF NOT EXISTS suspects (
    suspect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    sex        TEXT    NOT NULL CHECK(sex IN ('M', 'F')),
    address    TEXT,
    occupation TEXT,
    age        INTEGER,
    height     TEXT,
    photo_path TEXT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    case_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT    UNIQUE NOT NULL,
    suspect_id  INTEGER REFERENCES suspects(suspect_id),
    officer_id  INTEGER REFERENCES officers(officer_id),
    crime_type  TEXT    NOT NULL,
    description TEXT,
    status      TEXT    NOT NULL CHECK(status IN ('Open', 'Under Investigation', 'Closed')),
    date_filed  DATE    NOT NULL
);

CREATE TABLE IF NOT EXISTS arrests (
    arrest_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    suspect_id  INTEGER REFERENCES suspects(suspect_id),
    officer_id  INTEGER REFERENCES officers(officer_id),
    case_id     INTEGER REFERENCES cases(case_id),
    arrest_date DATE    NOT NULL,
    location    TEXT    NOT NULL,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS wanted_persons (
    wanted_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    suspect_id    INTEGER REFERENCES suspects(suspect_id),
    crime_type    TEXT    NOT NULL,
    reward_amount REAL,
    last_seen     TEXT,
    status        TEXT    NOT NULL CHECK(status IN ('At Large', 'Captured')),
    date_added    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cases_status     ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_suspect    ON cases(suspect_id);
CREATE INDEX IF NOT EXISTS idx_cases_officer    ON cases(officer_id);
CREATE INDEX IF NOT EXISTS idx_arrests_case     ON arrests(case_id);
CREATE INDEX IF NOT EXISTS idx_arrests_suspect  ON arrests(suspect_id);
CREATE INDEX IF NOT EXISTS idx_wanted_suspect   ON wanted_persons(suspect_id);
"""

# Table display names, used by the UI and by the confirmation dialogs.
TABLE_LABELS: dict[str, str] = {
    "users": "User Account",
    "officers": "Officer",
    "suspects": "Suspect",
    "cases": "Case File",
    "arrests": "Arrest Record",
    "wanted_persons": "Wanted Person Entry",
}

# Child tables that point at a parent table.  Used to warn the operator before a
# delete and (optionally) to cascade the delete so no orphan rows are left.
CHILD_REFERENCES: dict[str, list[tuple[str, str]]] = {
    "suspects": [
        ("cases", "suspect_id"),
        ("arrests", "suspect_id"),
        ("wanted_persons", "suspect_id"),
    ],
    "officers": [
        ("cases", "officer_id"),
        ("arrests", "officer_id"),
    ],
    "cases": [
        ("arrests", "case_id"),
    ],
    "arrests": [],
    "wanted_persons": [],
    "users": [],
}

# Primary-key column of each table.
PRIMARY_KEYS: dict[str, str] = {
    "users": "user_id",
    "officers": "officer_id",
    "suspects": "suspect_id",
    "cases": "case_id",
    "arrests": "arrest_id",
    "wanted_persons": "wanted_id",
}

ALLOWED_TABLES = tuple(TABLE_LABELS.keys())


# --------------------------------------------------------------------------- #
#  Low level helpers
# --------------------------------------------------------------------------- #
def validate_identifier(name: str) -> str:
    """
    Guard against SQL injection through dynamic identifiers.

    Only identifiers that appear in the module-level whitelists are accepted.
    Raises ``ValueError`` otherwise.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Identifier must be a non-empty string.")
    safe = name.strip()
    if not (safe.replace("_", "").isalnum() and not safe[0].isdigit()):
        raise ValueError(f"Unsafe SQL identifier rejected: {name!r}")
    return safe


def validate_table(table: str) -> str:
    """Validate a table name against the known tables of this application."""
    safe = validate_identifier(table)
    if safe not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table!r}")
    return safe


def ensure_photos_dir() -> str:
    """Create the ``photos/`` folder if it does not exist and return its path."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    return PHOTOS_DIR


def get_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection to the application database.

    The row factory is set to ``sqlite3.Row`` so results can be accessed both by
    index and by column name (``row["name"]``), and foreign-key enforcement is
    switched on for this connection.
    """
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_query(query: str, params: Sequence[Any] | dict[str, Any] = ()) -> int:
    """
    Run an INSERT / UPDATE / DELETE statement and commit it.

    Returns
    -------
    int
        ``cursor.lastrowid`` for INSERT statements, otherwise the number of
        affected rows (``cursor.rowcount``).
    """
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid if cur.lastrowid else cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_many(query: str, seq_of_params: Iterable[Sequence[Any]]) -> int:
    """Run the same statement for many parameter sets inside one transaction."""
    conn = get_connection()
    try:
        cur = conn.executemany(query, seq_of_params)
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[sqlite3.Row]:
    """Return every row produced by ``query`` as a list of ``sqlite3.Row``."""
    conn = get_connection()
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def fetch_one(query: str, params: Sequence[Any] | dict[str, Any] = ()) -> Optional[sqlite3.Row]:
    """Return the first row produced by ``query`` (or ``None``)."""
    conn = get_connection()
    try:
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()


def fetch_value(query: str, params: Sequence[Any] | dict[str, Any] = (), default: Any = None) -> Any:
    """Return a single scalar value from the first column of the first row."""
    row = fetch_one(query, params)
    if row is None:
        return default
    value = row[0]
    return default if value is None else value


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert an iterable of ``sqlite3.Row`` objects into plain dictionaries."""
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
#  Convenience query helpers used by the UI
# --------------------------------------------------------------------------- #
def table_exists(table: str) -> bool:
    """Return True when ``table`` exists in the database file."""
    try:
        safe = validate_identifier(table)
    except ValueError:
        return False
    row = fetch_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (safe,),
    )
    return row is not None


def database_ready() -> bool:
    """True when every application table exists (i.e. setup_db.py has run)."""
    return all(table_exists(t) for t in ALLOWED_TABLES)


def count_rows(table: str, where: str = "", params: Sequence[Any] = ()) -> int:
    """Return the number of rows in ``table``, optionally filtered by ``where``."""
    safe = validate_table(table)
    clause = f" WHERE {where}" if where else ""
    return int(fetch_value(f"SELECT COUNT(*) FROM {safe}{clause}", params, 0))


def child_counts(table: str, pk_value: int) -> list[tuple[str, str, int]]:
    """
    Return ``(child_table, fk_column, count)`` for every table that references
    the given parent row.  Only non-zero counts are returned.
    """
    safe = validate_table(table)
    found: list[tuple[str, str, int]] = []
    for child_table, fk_col in CHILD_REFERENCES.get(safe, []):
        n = count_rows(child_table, f"{fk_col} = ?", (pk_value,))
        if n:
            found.append((child_table, fk_col, n))
    return found


def delete_record(table: str, pk_value: int, cascade: bool = False) -> int:
    """
    Delete one row from ``table``.

    Parameters
    ----------
    table : str
        Target table (validated against the whitelist).
    pk_value : int
        Value of the primary key of the row to remove.
    cascade : bool
        When True, rows in child tables that reference this record are deleted
        first, which keeps the foreign keys consistent.

    Returns
    -------
    int
        Number of rows deleted from ``table``.

    Raises
    ------
    sqlite3.IntegrityError
        When ``cascade`` is False and child rows still reference the record.
    """
    safe = validate_table(table)
    pk_col = PRIMARY_KEYS[safe]
    conn = get_connection()
    try:
        if cascade:
            for child_table, fk_col in CHILD_REFERENCES.get(safe, []):
                conn.execute(f"DELETE FROM {child_table} WHERE {fk_col} = ?", (pk_value,))
        cur = conn.execute(f"DELETE FROM {safe} WHERE {pk_col} = ?", (pk_value,))
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
#  Schema creation / reset
# --------------------------------------------------------------------------- #
def init_db(verbose: bool = False) -> None:
    """Create every table, index and the ``photos/`` directory if missing."""
    ensure_photos_dir()
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        if verbose:
            print("[db] Schema verified - all tables are present.")
    finally:
        conn.close()


def reset_db(verbose: bool = False) -> None:
    """
    Drop every application table and recreate the empty schema.

    Foreign-key enforcement is switched off for the duration of the drop
    (SQLite runs an implicit ``DELETE FROM`` when a table is dropped, which
    would otherwise trip the child rows), and the tables are removed
    child-first so the operation is tidy either way.
    """
    # Drop children before their parents.
    drop_order = [
        "wanted_persons", "arrests", "cases", "suspects", "officers", "users",
    ]

    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    try:
        conn.isolation_level = None          # autocommit: the PRAGMA must apply at once
        conn.execute("PRAGMA foreign_keys = OFF;")
        for table in drop_order:
            conn.execute(f"DROP TABLE IF EXISTS {validate_identifier(table)};")
        conn.execute("PRAGMA foreign_keys = ON;")
        if verbose:
            print("[db] All tables dropped.")
    finally:
        conn.close()
    init_db(verbose=verbose)


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    init_db(verbose=True)
    print(f"[db] Database file : {DB_PATH}")
    print(f"[db] Photos folder : {PHOTOS_DIR}")
    for t in ALLOWED_TABLES:
        print(f"[db]   {t:<16} rows = {count_rows(t)}")
