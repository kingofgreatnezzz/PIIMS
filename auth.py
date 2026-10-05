"""
auth.py
=======
Authentication and role handling for the
POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS).

Security approach
-----------------
Passwords are never stored in clear text.  Each password is hashed with
PBKDF2-HMAC-SHA256 using a fresh 16-byte random salt and 200 000 iterations
(OWASP recommended minimum for PBKDF2-SHA256).  The stored value is a single
self-describing string:

        pbkdf2_sha256$200000$<salt-hex>$<derived-key-hex>

Verification uses :func:`hmac.compare_digest` so that comparison time does not
leak information about the stored hash.

Only ``hashlib``/``hmac``/``os`` from the Python standard library are used -
no third-party crypto dependency is required.

Public API
----------
hash_password(password)                  -> str
check_password(password, password_hash)  -> bool
login_user(username, password)           -> dict | None      (pure function)
get_current_user()                       -> dict | None      (st.session_state)
session_login(user) / logout_user()
is_admin() / is_viewer() / require_admin()
create_user(...) / change_password(...) / list_users() / delete_user()
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Optional

import streamlit as st

from db import execute_query, fetch_all, fetch_one, rows_to_dicts

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
PBKDF2_ALGORITHM: str = "pbkdf2_sha256"
PBKDF2_ITERATIONS: int = 200_000
SALT_BYTES: int = 16
MIN_PASSWORD_LENGTH: int = 6

ROLES: tuple[str, ...] = ("Admin", "Viewer")

# Session-state key that holds the signed-in user dictionary.
SESSION_KEY: str = "auth_user"


# --------------------------------------------------------------------------- #
#  Password hashing / verification
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """
    Hash ``password`` with PBKDF2-HMAC-SHA256 and a random salt.

    Raises
    ------
    ValueError
        If the password is empty or shorter than ``MIN_PASSWORD_LENGTH``.
    """
    if not isinstance(password, str) or not password.strip():
        raise ValueError("Password must not be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )

    salt: bytes = os.urandom(SALT_BYTES)
    derived: bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def check_password(password: str, password_hash: str) -> bool:
    """
    Verify ``password`` against a stored hash produced by :func:`hash_password`.

    Also understands the legacy ``sha256$<hex>`` format (a single unsalted
    SHA-256 digest) so that databases created by an earlier prototype can still
    be opened.  Every failure mode returns ``False`` rather than raising, which
    keeps the login form free of confusing tracebacks.
    """
    if not password or not password_hash:
        return False

    try:
        parts = str(password_hash).split("$")

        # ---- Modern format: pbkdf2_sha256$iterations$salt$key ------------ #
        if len(parts) == 4 and parts[0] == PBKDF2_ALGORITHM:
            _, iterations, salt_hex, expected_hex = parts
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return hmac.compare_digest(derived.hex(), expected_hex)

        # ---- Legacy format: sha256$<hex> --------------------------------- #
        if len(parts) == 2 and parts[0] == "sha256":
            digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest, parts[1])

        # ---- Legacy format: bare sha256 hex digest ----------------------- #
        if len(parts) == 1 and len(parts[0]) == 64:
            digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest, parts[0])

    except (ValueError, TypeError):
        return False

    return False


# --------------------------------------------------------------------------- #
#  User records
# --------------------------------------------------------------------------- #
def login_user(username: str, password: str) -> Optional[dict[str, Any]]:
    """
    Authenticate a user against the ``users`` table.

    This is a *pure* function: it does not touch ``st.session_state`` so it can
    be reused in scripts and tests.  Call :func:`session_login` afterwards to
    record the session.

    Returns
    -------
    dict | None
        ``{"user_id", "username", "role", "created_at"}`` on success,
        otherwise ``None``.
    """
    if not username or not password:
        return None

    row = fetch_one(
        "SELECT user_id, username, password_hash, role, created_at "
        "FROM users WHERE LOWER(username) = LOWER(?)",
        (username.strip(),),
    )
    if row is None:
        return None

    if not check_password(password, row["password_hash"]):
        return None

    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    """Fetch a single user record by primary key."""
    row = fetch_one(
        "SELECT user_id, username, role, created_at FROM users WHERE user_id = ?",
        (user_id,),
    )
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    """Return every user account (without password hashes)."""
    return rows_to_dicts(
        fetch_all(
            "SELECT user_id, username, role, created_at FROM users ORDER BY user_id"
        )
    )


def username_exists(username: str, exclude_user_id: Optional[int] = None) -> bool:
    """True when ``username`` is already taken by another account."""
    if exclude_user_id is None:
        row = fetch_one(
            "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)",
            (username.strip(),),
        )
    else:
        row = fetch_one(
            "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?) AND user_id <> ?",
            (username.strip(), exclude_user_id),
        )
    return row is not None


def create_user(username: str, password: str, role: str) -> int:
    """
    Create a new user account and return its ``user_id``.

    Raises
    ------
    ValueError
        For an invalid role, blank username, weak password or duplicate name.
    """
    username = (username or "").strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {', '.join(ROLES)}.")
    if username_exists(username):
        raise ValueError(f"Username '{username}' already exists.")

    password_hash = hash_password(password)
    return int(
        execute_query(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
    )


def change_password(user_id: int, new_password: str) -> None:
    """Set a new password for ``user_id``."""
    execute_query(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (hash_password(new_password), user_id),
    )


def delete_user(user_id: int) -> None:
    """
    Delete a user account.

    Raises
    ------
    ValueError
        If the account is the last remaining administrator.
    """
    row = fetch_one("SELECT role FROM users WHERE user_id = ?", (user_id,))
    if row is None:
        raise ValueError("That user account no longer exists.")
    if row["role"] == "Admin" and count_admins() <= 1:
        raise ValueError("Cannot delete the last remaining administrator account.")
    execute_query("DELETE FROM users WHERE user_id = ?", (user_id,))


def count_admins() -> int:
    """Number of accounts whose role is Admin."""
    row = fetch_one("SELECT COUNT(*) AS n FROM users WHERE role = 'Admin'")
    return int(row["n"]) if row else 0


# --------------------------------------------------------------------------- #
#  Session management (st.session_state)
# --------------------------------------------------------------------------- #
def session_login(user: dict[str, Any]) -> None:
    """Record an authenticated user in the Streamlit session."""
    st.session_state[SESSION_KEY] = dict(user)
    st.session_state["login_time"] = True
    st.session_state["failed_logins"] = 0


def logout_user() -> None:
    """Clear the authenticated user and all page state from the session."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_current_user() -> Optional[dict[str, Any]]:
    """Return the signed-in user dictionary, or ``None`` when not signed in."""
    try:
        user = st.session_state.get(SESSION_KEY)
    except Exception:  # pragma: no cover - session unavailable outside a run
        return None
    return dict(user) if isinstance(user, dict) else None


def is_logged_in() -> bool:
    """True when a user is signed in."""
    return get_current_user() is not None


def current_role() -> str:
    """Role of the signed-in user (``""`` when not signed in)."""
    user = get_current_user()
    return user["role"] if user else ""


def is_admin() -> bool:
    """True when the signed-in user has full (write) privileges."""
    return current_role() == "Admin"


def is_viewer() -> bool:
    """True when the signed-in user has read-only privileges."""
    return current_role() == "Viewer"


def require_admin() -> bool:
    """
    Guard helper for write operations.

    Renders an error message and returns ``False`` when the current user is not
    an administrator, so callers can simply ``return`` early.
    """
    if not is_admin():
        st.error("🔒 Access denied. This action requires Administrator privileges.")
        return False
    return True
