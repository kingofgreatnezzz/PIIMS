"""
app.py
======
POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS)
Nigeria Police Force - Oji-River Area Command, Oji-River LGA, Enugu State.

A single-file Streamlit front-end providing:

    * Secured sign-in for two roles (Admin = full access, Viewer = read only)
    * Command dashboard with the four key performance indicators
    * Case file management           (create / read / update / delete)
    * Arrest record management       (create / read / update / delete)
    * Wanted persons register        (with suspect photographs)
    * Officer / personnel records    (with caseload analysis)
    * Suspect records                (with photograph upload)
    * Command-wide search and retrieval
    * Computerized Intelligence Report generator (HTML / PDF / TXT)

Run with:      streamlit run app.py
or simply:     setup_and_start.bat

Stack: Python 3.10+, Streamlit, SQLite (stdlib), Pandas, Pillow.
"""

from __future__ import annotations

import base64
import datetime as dt
import io
import os
import sqlite3
import time
from html import escape as html_escape
from typing import Any, Callable, Optional

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
#  Page configuration - MUST be the first Streamlit call in the script
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="NPF PIIMS | Oji-River Area Command",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from PIL import Image  # noqa: E402  (imported after set_page_config by design)

import auth  # noqa: E402
import db  # noqa: E402
import reports as R  # noqa: E402
import setup_db  # noqa: E402

# --------------------------------------------------------------------------- #
#  Domain constants - Oji-River Area Command
# --------------------------------------------------------------------------- #
CRIME_TYPES: list[str] = ["Armed Robbery", "Fraud", "Assault", "Theft", "Kidnapping"]
LOCATIONS: list[str] = ["Oji-River Town", "Ndeaboh", "Agbani", "Udi", "Akegbe Ugwu"]
DEPARTMENTS: list[str] = ["Intelligence", "Crime Investigation", "Fraud Investigation"]
CASE_STATUSES: list[str] = ["Open", "Under Investigation", "Closed"]
WANTED_STATUSES: list[str] = ["At Large", "Captured"]
SEXES: list[str] = ["M", "F"]
SEX_LABELS: dict[str, str] = {"M": "Male", "F": "Female"}
RANKS: list[str] = [
    "Inspector",
    "Sergeant",
    "Assistant Superintendent of Police",
    "Deputy Superintendent of Police",
    "Superintendent of Police",
]
RANK_ABBR: dict[str, str] = {
    "Inspector": "Insp.",
    "Sergeant": "Sgt.",
    "Assistant Superintendent of Police": "ASP",
    "Deputy Superintendent of Police": "DSP",
    "Superintendent of Police": "SP",
}
ORG_NAME = "Nigeria Police Force"
ORG_UNIT = "Police Command Oji-River, Oji-River LGA, Enugu State"

NAV_ITEMS: list[tuple[str, str, tuple[str, ...]]] = [
    # (page key, sidebar label, roles allowed)
    ("Dashboard", "🏠 Command Dashboard", ("Admin", "Viewer")),
    ("Case Files", "🗂️ Case Files", ("Admin", "Viewer")),
    ("Arrest Records", "🚔 Arrest Records", ("Admin", "Viewer")),
    ("Wanted Persons", "🎯 Wanted Persons", ("Admin", "Viewer")),
    ("Officers", "👮 Officers & Personnel", ("Admin", "Viewer")),
    ("Suspects", "🧾 Suspect Records", ("Admin", "Viewer")),
    ("Search & Retrieve", "🔍 Search & Retrieve", ("Admin", "Viewer")),
    ("Intelligence Report", "📄 Intelligence Report", ("Admin", "Viewer")),
    ("User Management", "👥 User Management", ("Admin",)),
]

# --------------------------------------------------------------------------- #
#  Streamlit version compatibility helpers
# --------------------------------------------------------------------------- #


def _st_version_tuple() -> tuple[int, int]:
    try:
        parts = st.__version__.split(".")
        return int(parts[0]), int(parts[1])
    except Exception:  # pragma: no cover - defensive
        return (1, 30)


# Streamlit 1.49 renamed ``use_container_width`` to ``width="stretch"``.
if _st_version_tuple() >= (1, 49):
    STRETCH: dict[str, Any] = {"width": "stretch"}
else:  # pragma: no cover - older Streamlit releases
    STRETCH = {"use_container_width": True}

DIALOG = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


# --------------------------------------------------------------------------- #
#  Styling
# --------------------------------------------------------------------------- #
APP_CSS = """
<style>
  :root {
    --npf-navy: #0b2545;
    --npf-navy-soft: #12335c;
    --npf-gold: #c9a227;
    --npf-green: #046a38;
    --npf-red: #b3261e;
  }
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1350px;}

  /* ---- command banner ------------------------------------------------- */
  .npf-banner {
    background: linear-gradient(100deg, var(--npf-navy) 0%, var(--npf-navy-soft) 60%, #1d4e89 100%);
    border-radius: 10px; padding: 18px 24px; margin-bottom: 18px;
    border-left: 8px solid var(--npf-gold);
    box-shadow: 0 2px 8px rgba(11, 37, 69, .25);
  }
  .npf-banner h1 {color: #ffffff; font-size: 1.45rem; margin: 0 0 4px 0; letter-spacing: .4px;}
  .npf-banner p {color: #d8e2ef; margin: 0; font-size: .87rem;}
  .npf-banner .badge {
    display:inline-block; background: var(--npf-gold); color: #1b1b1b; font-weight: 700;
    border-radius: 20px; padding: 2px 12px; font-size: .72rem; letter-spacing: .6px;
    margin-top: 8px;
  }

  /* ---- metric cards --------------------------------------------------- */
  div[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #dde3ea; border-left: 6px solid var(--npf-navy);
    border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 4px rgba(11,37,69,.08);
  }
  div[data-testid="stMetricLabel"] p {font-size: .82rem !important; font-weight: 600; color: #4a5568;}
  div[data-testid="stMetricValue"] {color: var(--npf-navy);}

  /* ---- generic content card ------------------------------------------- */
  .npf-card {
    background: #ffffff; border: 1px solid #dde3ea; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(11,37,69,.07);
  }
  .npf-card h4 {margin: 0 0 8px 0; color: var(--npf-navy); font-size: 1rem;}
  .npf-card .meta {color: #5a6472; font-size: .82rem; margin: 2px 0;}

  /* ---- activity feed -------------------------------------------------- */
  .feed-item {
    border-left: 4px solid var(--npf-green); background: #f8fafc;
    padding: 8px 12px; margin-bottom: 8px; border-radius: 0 6px 6px 0;
  }
  .feed-item .title {font-weight: 700; color: var(--npf-navy); font-size: .9rem;}
  .feed-item .sub {color: #5a6472; font-size: .8rem;}

  /* ---- status pills --------------------------------------------------- */
  .pill {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: .72rem; font-weight: 700; letter-spacing: .3px;
  }
  .pill-open {background: #fdecea; color: #b3261e;}
  .pill-progress {background: #fff4e0; color: #a15c00;}
  .pill-closed {background: #e6f4ea; color: #046a38;}
  .pill-captured {background: #e6f4ea; color: #046a38;}
  .pill-large {background: #fdecea; color: #b3261e;}

  /* ---- login ---------------------------------------------------------- */
  .login-shell {
    background: #ffffff; border-top: 7px solid var(--npf-navy);
    border-radius: 10px; padding: 26px 30px 10px 30px;
    box-shadow: 0 4px 18px rgba(11,37,69,.16);
  }
  .login-shell h2 {color: var(--npf-navy); margin-bottom: 2px; font-size: 1.25rem;}
  .login-shell p {color: #5a6472; font-size: .85rem;}

  /* ---- sidebar -------------------------------------------------------- */
  section[data-testid="stSidebar"] {background: #f5f7fa; border-right: 1px solid #dde3ea;}
  .side-brand {font-weight: 800; color: var(--npf-navy); font-size: 1rem; letter-spacing: .3px;}
  .side-sub {color: #5a6472; font-size: .75rem;}
  .side-user {
    background: var(--npf-navy); color: #fff; border-radius: 8px; padding: 10px 12px;
    margin: 8px 0 12px 0;
  }
  .side-user .role {color: var(--npf-gold); font-weight: 700; font-size: .78rem;}
</style>
"""


def inject_css() -> None:
    """Apply the application stylesheet."""
    st.markdown(APP_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Small utilities
# --------------------------------------------------------------------------- #
def esc(value: Any) -> str:
    """HTML-escape a value for safe embedding."""
    return html_escape("" if value is None else str(value))


def flash(kind: str, message: str) -> None:
    """Queue a message that is displayed once, after the next re-run."""
    st.session_state["flash_message"] = (kind, message)


def show_flash() -> None:
    """Display and clear any queued flash message."""
    payload = st.session_state.pop("flash_message", None)
    if not payload:
        return
    kind, message = payload
    {"success": st.success, "error": st.error, "warning": st.warning, "info": st.info}.get(
        kind, st.info
    )(message)


def bump(key: str) -> None:
    """
    Increment a counter used inside widget keys.

    Changing the key forces Streamlit to build fresh widgets, which is how the
    forms are cleared after a successful insert.
    """
    st.session_state[key] = int(st.session_state.get(key, 0)) + 1


def vkey(base: str) -> str:
    """Return a versioned widget-key base so old widget state cannot linger."""
    return f"{base}_{st.session_state.get('form_version_' + base, 0)}"


def to_date(value: Any, default: Optional[dt.date] = None) -> dt.date:
    """Convert an ISO string / date / datetime into a ``datetime.date``."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return default or dt.date.today()


def fmt_date(value: Any, fallback: str = "-") -> str:
    """Render a stored date as ``05/10/2026``."""
    try:
        return to_date(value).strftime("%d/%m/%Y")
    except Exception:
        return fallback


def fmt_stamp(value: Any, fallback: str = "-") -> str:
    """Render a stored timestamp as ``05/10/2026 14:22``."""
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        return dt.datetime.fromisoformat(text[:19]).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return text


def naira(amount: Any) -> str:
    """Format a numeric amount as Naira, e.g. ``NGN 250,000.00``."""
    try:
        return f"NGN {float(amount):,.2f}"
    except (TypeError, ValueError):
        return "NGN 0.00"


def officer_display(name: Any, rank: Any = "", number: Any = "") -> str:
    """Build a printable officer string: ``DSP Musa Ibrahim (No. 0785124)``."""
    rank_text = RANK_ABBR.get(str(rank), str(rank or "")).strip()
    base = f"{rank_text} {name}".strip() if rank_text else str(name or "-")
    return f"{base} (No. {number})" if number else base


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serialise a dataframe to CSV bytes (UTF-8 with BOM so Excel opens it)."""
    return frame.to_csv(index=False).encode("utf-8-sig")


def download_csv(frame: pd.DataFrame, filename: str, label: str = "⬇️ Download as CSV") -> None:
    """Render a CSV download button for a dataframe."""
    if frame is None or frame.empty:
        return
    st.download_button(label, data=csv_bytes(frame), file_name=filename, mime="text/csv")


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    """Render the standard page banner."""
    st.markdown(
        f"""
        <div class="npf-banner">
          <h1>{esc(icon)} {esc(title)}</h1>
          <p>{esc(subtitle or ORG_UNIT)}</p>
          <span class="badge">{esc(ORG_NAME).upper()}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str) -> str:
    """Return HTML for a colour-coded status pill."""
    mapping = {
        "Open": "pill-open",
        "Under Investigation": "pill-progress",
        "Closed": "pill-closed",
        "Captured": "pill-captured",
        "At Large": "pill-large",
    }
    css = mapping.get(str(status), "pill-progress")
    return f'<span class="pill {css}">{esc(status)}</span>'


def empty_state(message: str, icon: str = "📭") -> None:
    """Render a friendly empty-state box."""
    st.info(f"{icon}  {message}")


def readonly_notice() -> None:
    """Explain the read-only restriction to Viewer accounts."""
    st.info(
        "👁️ **Read-only session.** You are signed in as a *Viewer*. "
        "You may view, filter, search and generate reports, but adding, editing "
        "and deleting records requires an Administrator account."
    )


# --------------------------------------------------------------------------- #
#  Photograph handling (Pillow)
# --------------------------------------------------------------------------- #
def absolute_photo_path(relative_path: Any) -> Optional[str]:
    """Resolve a stored ``photos/xxx.jpg`` path against the project folder."""
    if not relative_path:
        return None
    text = str(relative_path)
    full = text if os.path.isabs(text) else os.path.join(db.BASE_DIR, text)
    return full if os.path.exists(full) else None


def photo_data_uri(relative_path: Any) -> Optional[str]:
    """Return a base64 ``data:`` URI for a stored photograph (or None)."""
    full = absolute_photo_path(relative_path)
    if not full:
        return None
    try:
        with open(full, "rb") as handle:
            payload = base64.b64encode(handle.read()).decode("ascii")
        extension = os.path.splitext(full)[1].lower().lstrip(".") or "jpeg"
        mime = "image/jpeg" if extension in ("jpg", "jpeg") else f"image/{extension}"
        return f"data:{mime};base64,{payload}"
    except OSError:
        return None


def save_suspect_photo(uploaded_file: Any, suspect_id: int) -> Optional[str]:
    """
    Store an uploaded photograph in ``photos/`` using Pillow.

    The image is converted to RGB, resized so its longest side is at most
    600 px (keeps the database folder small) and written as JPEG.  Returns the
    project-relative path that is stored in ``suspects.photo_path``.
    """
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.load()
    except Exception as error:
        raise ValueError(f"That file could not be read as an image ({error}).") from error

    image = image.convert("RGB")
    image.thumbnail((600, 600), Image.Resampling.LANCZOS)

    db.ensure_photos_dir()
    filename = f"suspect_{int(suspect_id):04d}_{int(time.time())}.jpg"
    full_path = os.path.join(db.PHOTOS_DIR, filename)
    image.save(full_path, "JPEG", quality=86, optimize=True)
    return f"photos/{filename}"


def remove_photo_file(relative_path: Any) -> None:
    """Delete a photograph from disk, ignoring a missing file."""
    full = absolute_photo_path(relative_path)
    if full:
        try:
            os.remove(full)
        except OSError:
            pass


def save_case_photo(uploaded_file: Any, case_id: int) -> Optional[str]:
    """
    Store a photograph attached to a CASE FILE in ``photos/`` using Pillow.

    This is the case-level evidence picture (a photograph of the scene, the
    recovered property or the exhibit) and is deliberately separate from the
    suspect's own photograph.  The image is converted to RGB, resized so its
    longest side is at most 900 px and written as JPEG.  Returns the
    project-relative path stored in ``cases.photo_path``.
    """
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.load()
    except Exception as error:
        raise ValueError(f"That file could not be read as an image ({error}).") from error

    image = image.convert("RGB")
    image.thumbnail((900, 900), Image.Resampling.LANCZOS)

    db.ensure_photos_dir()
    filename = f"case_{int(case_id):04d}_{int(time.time())}.jpg"
    full_path = os.path.join(db.PHOTOS_DIR, filename)
    image.save(full_path, "JPEG", quality=86, optimize=True)
    return f"photos/{filename}"


# --------------------------------------------------------------------------- #
#  Lookup helpers - build label -> id maps for the select boxes
# --------------------------------------------------------------------------- #
def suspect_choices(include_blank: bool = False) -> dict[str, Optional[int]]:
    """Return ``{label: suspect_id}`` for every suspect on record."""
    rows = db.fetch_all(
        "SELECT suspect_id, name, sex, address FROM suspects ORDER BY name COLLATE NOCASE"
    )
    options: dict[str, Optional[int]] = {}
    if include_blank:
        options["-- Select suspect --"] = None
    for row in rows:
        label = (
            f"SUS-{int(row['suspect_id']):03d} | {row['name']} "
            f"({SEX_LABELS.get(row['sex'], row['sex'])}) - {row['address'] or 'address not stated'}"
        )
        options[label] = int(row["suspect_id"])
    return options


def officer_choices(include_blank: bool = False) -> dict[str, Optional[int]]:
    """Return ``{label: officer_id}`` for every officer in the command."""
    rows = db.fetch_all(
        "SELECT officer_id, officer_number, name, rank, department "
        "FROM officers ORDER BY name COLLATE NOCASE"
    )
    options: dict[str, Optional[int]] = {}
    if include_blank:
        options["-- Select officer --"] = None
    for row in rows:
        label = (
            f"OFF-{int(row['officer_id']):03d} | {RANK_ABBR.get(row['rank'], row['rank'])} "
            f"{row['name']} (No. {row['officer_number']}) - {row['department']}"
        )
        options[label] = int(row["officer_id"])
    return options


def case_choices(include_blank: bool = False) -> dict[str, Optional[int]]:
    """Return ``{label: case_id}`` for every case file."""
    rows = db.fetch_all(
        """
        SELECT c.case_id, c.case_number, c.crime_type, c.status,
               COALESCE(s.name, 'suspect not recorded') AS suspect_name
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        ORDER BY c.case_number DESC
        """
    )
    options: dict[str, Optional[int]] = {}
    if include_blank:
        options["-- Select case file --"] = None
    for row in rows:
        label = (
            f"{row['case_number']} | {row['crime_type']} - {row['suspect_name']} "
            f"[{row['status']}]"
        )
        options[label] = int(row["case_id"])
    return options


def label_for(mapping: dict[str, Optional[int]], value: Any) -> Optional[str]:
    """Reverse lookup: find the label whose id equals ``value``."""
    for label, identifier in mapping.items():
        if identifier == value:
            return label
    return None


def index_for(mapping: dict[str, Optional[int]], value: Any) -> int:
    """Index of ``value`` inside a choice mapping (0 when not found)."""
    for position, identifier in enumerate(mapping.values()):
        if identifier == value:
            return position
    return 0


def require_records(kind: str, mapping: dict[str, Optional[int]], hint: str = "") -> bool:
    """Guard: stop an add-form when the referenced table is still empty."""
    if len([v for v in mapping.values() if v is not None]) == 0:
        st.warning(f"⚠️ No {kind} available yet. {hint}")
        return False
    return True


def suggest_case_number() -> str:
    """Suggest the next case number in the ``OR/<year>/<serial>`` format."""
    year = dt.date.today().year
    row = db.fetch_one(
        "SELECT case_number FROM cases WHERE case_number LIKE ? "
        "ORDER BY case_number DESC LIMIT 1",
        (f"OR/{year}/%",),
    )
    serial = 1
    if row:
        try:
            serial = int(str(row["case_number"]).split("/")[-1]) + 1
        except (ValueError, IndexError):
            serial = db.count_rows("cases") + 1
    return f"OR/{year}/{serial:03d}"


# --------------------------------------------------------------------------- #
#  Deletion workflow (confirmation dialog)
# --------------------------------------------------------------------------- #
def request_delete(table: str, pk_value: int, label: str) -> None:
    """Queue a record for deletion and trigger the confirmation dialog."""
    st.session_state["pending_delete"] = {
        "table": table,
        "pk_col": db.PRIMARY_KEYS[table],
        "pk_value": int(pk_value),
        "label": label,
    }
    st.rerun()


def _perform_delete(pending: dict[str, Any], cascade: bool) -> str:
    """Execute the queued deletion and return a success description."""
    table = pending["table"]
    value = pending["pk_value"]
    if table == "users":
        auth.delete_user(value)
        return f"User account '{pending['label']}' has been deleted."

    # Remove any photograph held on disk BEFORE the row disappears, otherwise
    # the file would be orphaned in photos/ with nothing pointing at it.
    if table in ("cases", "suspects"):
        try:
            photo_row = db.fetch_one(
                f"SELECT photo_path FROM {table} WHERE "
                f"{'case_id' if table == 'cases' else 'suspect_id'} = ?", (value,))
            if photo_row and photo_row["photo_path"]:
                remove_photo_file(photo_row["photo_path"])
        except Exception:  # noqa: BLE001 - never block the deletion itself
            pass

    removed = db.delete_record(table, value, cascade=cascade)
    return f"{db.TABLE_LABELS.get(table, 'Record')} deleted successfully ({removed} row(s) removed)."


def _confirm_delete_body(pending: dict[str, Any]) -> None:
    """Shared body for the delete confirmation (dialog or inline fallback)."""
    table = pending["table"]
    value = pending["pk_value"]
    label = pending["label"]

    st.markdown(f"**Record:** {esc(label)}")
    st.caption(f"Table: `{table}`  |  Primary key: `{pending['pk_col']} = {value}`")

    children = db.child_counts(table, value)
    cascade = False
    if children:
        st.warning(
            "This record is still referenced by: "
            + ", ".join(f"**{t.replace('_', ' ')}** ({n} record(s))" for t, _, n in children)
        )
        cascade = st.checkbox(
            "Also delete the linked records listed above (cascade delete)",
            key=f"cascade_{table}_{value}",
            help="Leave this unticked to abort. The database enforces foreign-key "
                 "integrity, so linked records must be removed together.",
        )

    st.error("⚠️ This action is permanent and cannot be undone.")

    left, right = st.columns(2)
    if left.button(
        "🗑️ Yes, delete permanently",
        key=f"confirm_del_{table}_{value}",
        type="primary",
        **STRETCH,
    ):
        try:
            message = _perform_delete(pending, cascade)
        except sqlite3.IntegrityError:
            st.error(
                "Deletion blocked by the database: linked records still reference this "
                "entry. Tick the cascade option above and try again."
            )
            return
        except ValueError as error:
            st.error(str(error))
            return
        except Exception as error:  # pragma: no cover - unexpected driver error
            st.error(f"Deletion failed: {error}")
            return
        st.session_state.pop("pending_delete", None)
        flash("success", message)
        st.rerun()

    if right.button("✖️ Cancel", key=f"cancel_del_{table}_{value}", **STRETCH):
        st.session_state.pop("pending_delete", None)
        st.rerun()


if DIALOG is not None:

    @DIALOG("⚠️ Confirm Deletion")
    def _confirm_delete_dialog(pending: dict[str, Any]) -> None:  # pragma: no cover
        _confirm_delete_body(pending)

else:  # pragma: no cover - only for very old Streamlit releases
    _confirm_delete_dialog = None


def render_pending_delete() -> None:
    """Open the delete confirmation for any queued record."""
    pending = st.session_state.get("pending_delete")
    if not isinstance(pending, dict):
        return
    if _confirm_delete_dialog is not None:
        _confirm_delete_dialog(pending)
    else:  # inline fallback
        st.markdown("---")
        with st.container(border=True):
            st.subheader("⚠️ Confirm Deletion")
            _confirm_delete_body(pending)


# --------------------------------------------------------------------------- #
#  Data access helpers
# --------------------------------------------------------------------------- #
def dashboard_stats() -> dict[str, int]:
    """Collect the four dashboard indicators (plus a little supporting detail)."""
    month_start = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    return {
        "active_cases": db.count_rows("cases", "status IN ('Open', 'Under Investigation')"),
        "open_cases": db.count_rows("cases", "status = 'Open'"),
        "investigating": db.count_rows("cases", "status = 'Under Investigation'"),
        "closed_cases": db.count_rows("cases", "status = 'Closed'"),
        "total_cases": db.count_rows("cases"),
        "arrests": db.count_rows("arrests"),
        "arrests_recent": db.count_rows("arrests", "arrest_date >= ?", (month_start,)),
        "wanted_large": db.count_rows("wanted_persons", "status = 'At Large'"),
        "wanted_captured": db.count_rows("wanted_persons", "status = 'Captured'"),
        "officers": db.count_rows("officers"),
        "suspects": db.count_rows("suspects"),
        "cases_recent": db.count_rows("cases", "date_filed >= ?", (month_start,)),
    }


def cases_frame(
    search: str = "",
    statuses: Optional[list[str]] = None,
    crime_types: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Return the case register as a display-ready dataframe."""
    sql = """
        SELECT c.case_id, c.case_number AS "Case Number", c.crime_type AS "Offence",
               COALESCE(s.name, 'Not recorded') AS "Suspect",
               COALESCE(o.name, 'Unassigned') AS "Investigating Officer",
               o.officer_number AS "Officer No.",
               c.status AS "Status", c.date_filed AS "Date Filed",
               CASE WHEN c.photo_path IS NOT NULL AND c.photo_path <> ''
                    THEN '📷 Attached' ELSE '-' END AS "Photo",
               c.description AS "Description"
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        LEFT JOIN officers o ON o.officer_id = c.officer_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search:
        sql += """
          AND (c.case_number LIKE ? OR c.crime_type LIKE ? OR c.description LIKE ?
               OR s.name LIKE ? OR o.name LIKE ? OR o.officer_number LIKE ?)
        """
        params.extend([f"%{search}%"] * 6)
    if statuses:
        sql += f" AND c.status IN ({','.join('?' * len(statuses))})"
        params.extend(statuses)
    if crime_types:
        sql += f" AND c.crime_type IN ({','.join('?' * len(crime_types))})"
        params.extend(crime_types)
    # Newest first.  case_id is the final tiebreaker so a case that was just
    # added always appears at the TOP of the register, never lost in the middle.
    sql += " ORDER BY c.date_filed DESC, c.case_number DESC, c.case_id DESC"

    rows = db.rows_to_dicts(db.fetch_all(sql, tuple(params)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Date Filed"] = frame["Date Filed"].apply(fmt_date)
        frame = frame.drop(columns=["case_id"])
    return frame


def arrests_frame(search: str = "", locations: Optional[list[str]] = None) -> pd.DataFrame:
    """Return the arrest register as a display-ready dataframe."""
    sql = """
        SELECT a.arrest_id, COALESCE(s.name, 'Not recorded') AS "Suspect",
               COALESCE(o.name, 'Unassigned') AS "Arresting Officer",
               o.officer_number AS "Officer No.",
               COALESCE(c.case_number, 'Not linked') AS "Case Number",
               a.arrest_date AS "Arrest Date", a.location AS "Location",
               a.notes AS "Notes"
        FROM arrests a
        LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
        LEFT JOIN officers o ON o.officer_id = a.officer_id
        LEFT JOIN cases c ON c.case_id = a.case_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search:
        sql += """
          AND (s.name LIKE ? OR o.name LIKE ? OR o.officer_number LIKE ?
               OR c.case_number LIKE ? OR a.location LIKE ? OR a.notes LIKE ?)
        """
        params.extend([f"%{search}%"] * 6)
    if locations:
        sql += f" AND a.location IN ({','.join('?' * len(locations))})"
        params.extend(locations)
    sql += " ORDER BY a.arrest_date DESC"

    rows = db.rows_to_dicts(db.fetch_all(sql, tuple(params)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Arrest Date"] = frame["Arrest Date"].apply(fmt_date)
        frame = frame.drop(columns=["arrest_id"])
    return frame


def wanted_frame(search: str = "", statuses: Optional[list[str]] = None) -> pd.DataFrame:
    """Return the wanted-persons register as a display-ready dataframe."""
    sql = """
        SELECT w.wanted_id, COALESCE(s.name, 'Not recorded') AS "Suspect",
               s.sex AS "Sex", w.crime_type AS "Offence",
               w.reward_amount AS "Reward (NGN)",
               w.last_seen AS "Last Seen Location", w.status AS "Status",
               w.date_added AS "Date Added", s.photo_path AS "photo_path"
        FROM wanted_persons w
        LEFT JOIN suspects s ON s.suspect_id = w.suspect_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search:
        sql += " AND (s.name LIKE ? OR w.crime_type LIKE ? OR w.last_seen LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if statuses:
        sql += f" AND w.status IN ({','.join('?' * len(statuses))})"
        params.extend(statuses)
    sql += " ORDER BY CASE w.status WHEN 'At Large' THEN 0 ELSE 1 END, w.date_added DESC"

    rows = db.rows_to_dicts(db.fetch_all(sql, tuple(params)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Reward (NGN)"] = frame["Reward (NGN)"].apply(naira)
        frame["Date Added"] = frame["Date Added"].apply(fmt_stamp)
    return frame


def suspects_frame(search: str = "", sexes: Optional[list[str]] = None) -> pd.DataFrame:
    """Return the suspect register as a display-ready dataframe."""
    sql = """
        SELECT s.suspect_id, s.name AS "Name", s.sex AS "Sex",
               s.address AS "Address", s.occupation AS "Occupation",
               s.age AS "Age", s.height AS "Height",
               (SELECT COUNT(*) FROM cases c WHERE c.suspect_id = s.suspect_id) AS "Cases",
               (SELECT COUNT(*) FROM arrests a WHERE a.suspect_id = s.suspect_id) AS "Arrests",
               CASE WHEN s.photo_path IS NOT NULL THEN 'On file' ELSE 'Not on file' END AS "Photograph",
               s.date_added AS "Date Added", s.photo_path AS "photo_path"
        FROM suspects s
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search:
        sql += " AND (s.name LIKE ? OR s.address LIKE ? OR s.occupation LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if sexes:
        sql += f" AND s.sex IN ({','.join('?' * len(sexes))})"
        params.extend(sexes)
    sql += " ORDER BY s.name COLLATE NOCASE"

    rows = db.rows_to_dicts(db.fetch_all(sql, tuple(params)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Sex"] = frame["Sex"].map(lambda v: SEX_LABELS.get(v, v))
        frame["Date Added"] = frame["Date Added"].apply(fmt_stamp)
    return frame


def officers_frame(search: str = "", departments: Optional[list[str]] = None) -> pd.DataFrame:
    """Return the personnel register, including caseload counts."""
    sql = """
        SELECT o.officer_id, o.officer_number AS "Officer No.", o.name AS "Name",
               o.rank AS "Rank", o.department AS "Department",
               o.date_joined AS "Date Joined",
               (SELECT COUNT(*) FROM cases c WHERE c.officer_id = o.officer_id) AS "Cases Handled",
               (SELECT COUNT(*) FROM cases c WHERE c.officer_id = o.officer_id
                  AND c.status IN ('Open', 'Under Investigation')) AS "Active Cases",
               (SELECT COUNT(*) FROM arrests a WHERE a.officer_id = o.officer_id) AS "Arrests Effected"
        FROM officers o
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search:
        sql += " AND (o.name LIKE ? OR o.officer_number LIKE ? OR o.rank LIKE ? OR o.department LIKE ?)"
        params.extend([f"%{search}%"] * 4)
    if departments:
        sql += f" AND o.department IN ({','.join('?' * len(departments))})"
        params.extend(departments)
    sql += " ORDER BY o.name COLLATE NOCASE"

    rows = db.rows_to_dicts(db.fetch_all(sql, tuple(params)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Rank"] = frame["Rank"].map(lambda r: f"{RANK_ABBR.get(r, r)} ({r})")
        frame["Date Joined"] = frame["Date Joined"].apply(fmt_date)
    return frame


def officer_case_load() -> pd.DataFrame:
    """Aggregate caseload per officer, for the dashboard chart."""
    rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT o.name AS "Officer",
                   o.department AS "Department",
                   COUNT(c.case_id) AS "Cases",
                   SUM(CASE WHEN c.status IN ('Open', 'Under Investigation') THEN 1 ELSE 0 END)
                       AS "Active"
            FROM officers o
            LEFT JOIN cases c ON c.officer_id = o.officer_id
            GROUP BY o.officer_id
            ORDER BY "Cases" DESC, o.name
            """
        )
    )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    for column in ("Cases", "Active"):
        frame[column] = frame[column].fillna(0).astype(int)
    return frame


def recent_activity(limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent case filings and arrests, newest first."""
    rows = db.fetch_all(
        """
        SELECT 'Case Filed' AS kind, c.date_filed AS event_date,
               c.case_number AS reference, COALESCE(s.name, 'Not recorded') AS subject,
               c.crime_type AS detail, c.status AS status
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        UNION ALL
        SELECT 'Arrest Made', a.arrest_date, COALESCE(c.case_number, 'Not linked'),
               COALESCE(s.name, 'Not recorded'), a.location, 'Arrest'
        FROM arrests a
        LEFT JOIN cases c ON c.case_id = a.case_id
        LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
        ORDER BY event_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    return db.rows_to_dicts(rows)


# --------------------------------------------------------------------------- #
#  PAGE: Dashboard
# --------------------------------------------------------------------------- #
def render_dashboard() -> None:
    """Command overview: four indicators, activity feed and analytics."""
    user = auth.get_current_user() or {}
    stats = dashboard_stats()

    page_header(
        "🏠",
        "Command Dashboard",
        f"{ORG_UNIT}  |  {dt.date.today().strftime('%d %B %Y')}  |  "
        f"Signed in as {user.get('username', '-')} ({user.get('role', '-')})",
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "🗂️ Total Active Cases",
            stats["active_cases"],
            delta=f"+{stats['cases_recent']} in last 30 days",
            help="Case files with status 'Open' or 'Under Investigation'.",
        )
    with col2:
        st.metric(
            "🚔 Total Arrests Made",
            stats["arrests"],
            delta=f"+{stats['arrests_recent']} in last 30 days",
            help="All arrest records entered by the command.",
        )
    with col3:
        st.metric(
            "🎯 Wanted Persons at Large",
            stats["wanted_large"],
            delta=f"{stats['wanted_captured']} captured",
            delta_color="inverse",
            help="Suspects on the wanted register whose status is 'At Large'.",
        )
    with col4:
        st.metric(
            "👮 Officers on Duty",
            stats["officers"],
            delta=f"{len(DEPARTMENTS)} departments",
            help="Officers currently attached to the Oji-River Area Command.",
        )

    st.markdown("")
    left, right = st.columns([1.45, 1], gap="large")

    # ---- recent activity feed ------------------------------------------- #
    with left:
        st.subheader("🕒 Recent Activity")
        st.caption("The five most recent case filings and arrests in the command.")
        activity = recent_activity(5)
        if not activity:
            empty_state("No activity has been recorded yet.")
        for item in activity:
            icon = "🗂️" if item["kind"] == "Case Filed" else "🚔"
            subtitle = (
                f"{item['detail']} &nbsp;•&nbsp; Suspect: {esc(item['subject'])}"
                if item["kind"] == "Case Filed"
                else f"Location: {esc(item['detail'])} &nbsp;•&nbsp; Suspect: {esc(item['subject'])}"
            )
            status_html = (
                status_pill(item["status"]) if item["kind"] == "Case Filed" else ""
            )
            st.markdown(
                f"""
                <div class="feed-item">
                  <div class="title">{icon} {esc(item['kind'])} — {esc(item['reference'])}
                    &nbsp; {status_html}</div>
                  <div class="sub">{subtitle}</div>
                  <div class="sub">Date: {esc(fmt_date(item['event_date']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---- status breakdown + caseload ------------------------------------ #
    with right:
        st.subheader("📊 Case Status Breakdown")
        breakdown = pd.DataFrame(
            {
                "Status": ["Open", "Under Investigation", "Closed"],
                "Cases": [stats["open_cases"], stats["investigating"], stats["closed_cases"]],
            }
        ).set_index("Status")
        st.bar_chart(breakdown, height=210)

        st.subheader("🧭 Command Strength")
        strength = pd.DataFrame(
            {
                "Item": [
                    "Officers attached",
                    "Suspects on record",
                    "Total case files",
                    "Arrests recorded",
                    "Wanted persons",
                ],
                "Count": [
                    stats["officers"],
                    stats["suspects"],
                    stats["total_cases"],
                    stats["arrests"],
                    stats["wanted_large"] + stats["wanted_captured"],
                ],
            }
        ).set_index("Item")
        st.dataframe(strength, **STRETCH)

    st.markdown("---")
    chart_col, load_col = st.columns([1, 1.3], gap="large")

    with chart_col:
        st.subheader("🔎 Case Distribution by Offence")
        crime_rows = db.rows_to_dicts(
            db.fetch_all(
                "SELECT crime_type AS \"Offence\", COUNT(*) AS \"Cases\" "
                "FROM cases GROUP BY crime_type ORDER BY \"Cases\" DESC"
            )
        )
        if crime_rows:
            st.bar_chart(pd.DataFrame(crime_rows).set_index("Offence"), height=260)
        else:
            empty_state("No case files captured yet.")

    with load_col:
        st.subheader("👮 Officer Case Load")
        load = officer_case_load()
        if load.empty:
            empty_state("No officers captured yet.")
        else:
            st.dataframe(load, hide_index=True, **STRETCH)
            download_csv(load, "officer_case_load.csv")

    st.markdown("---")
    st.caption(
        f"🏛️ {ORG_NAME} — {ORG_UNIT}  |  PIIMS v1.0  |  "
        f"Database: `{os.path.basename(db.DB_PATH)}`  |  "
        f"Records: {stats['total_cases']} cases, {stats['arrests']} arrests, "
        f"{stats['suspects']} suspects, {stats['officers']} officers"
    )


# --------------------------------------------------------------------------- #
#  PAGE: Case files
# --------------------------------------------------------------------------- #
def _case_view_tab() -> None:
    """Searchable, filterable case register."""
    filter_a, filter_b, filter_c = st.columns([2, 1, 1])
    search = filter_a.text_input(
        "🔍 Search case files",
        placeholder="Case number, offence, suspect, officer or keyword...",
        key="case_search",
    )
    statuses = filter_b.multiselect("Filter by status", CASE_STATUSES, key="case_status_filter")
    crimes = filter_c.multiselect("Filter by offence", CRIME_TYPES, key="case_crime_filter")

    frame = cases_frame(search, statuses, crimes)
    if frame.empty:
        empty_state("No case file matches the current filter.", "🗂️")
        return

    st.caption(f"📌 {len(frame)} case file(s) displayed.")
    st.dataframe(frame, hide_index=True, height=380, **STRETCH)
    download_csv(frame, "case_files.csv")

    st.markdown("#### 🔎 Full case details")
    options = case_choices()
    label = st.selectbox("Select a case file to inspect", list(options.keys()), key="case_detail_pick")
    case_id = options[label]
    row = db.fetch_one(
        """
        SELECT c.case_id, c.case_number, c.crime_type, c.description, c.status,
               c.date_filed, c.photo_path AS case_photo_path,
               s.name AS suspect_name, s.sex, s.address, s.occupation, s.age,
               s.height, s.photo_path AS suspect_photo_path,
               o.name AS officer_name, o.officer_number, o.rank, o.department
        FROM cases c
        LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
        LEFT JOIN officers o ON o.officer_id = c.officer_id
        WHERE c.case_id = ?
        """,
        (case_id,),
    )
    if row:
        detail_left, detail_right = st.columns([2.2, 1])
        with detail_left:
            st.markdown(
                f"""
                <div class="npf-card">
                  <h4>{esc(row['case_number'])} — {esc(row['crime_type'])}
                      {status_pill(row['status'])}</h4>
                  <div class="meta"><strong>Suspect:</strong> {esc(row['suspect_name'] or 'Not recorded')}
                      &nbsp;|&nbsp; <strong>Sex:</strong> {esc(SEX_LABELS.get(row['sex'], '-'))}
                      &nbsp;|&nbsp; <strong>Age:</strong> {esc(row['age'] or '-')}</div>
                  <div class="meta"><strong>Address:</strong> {esc(row['address'] or '-')}</div>
                  <div class="meta"><strong>Occupation:</strong> {esc(row['occupation'] or '-')}</div>
                  <div class="meta"><strong>Investigating officer:</strong>
                      {esc(officer_display(row['officer_name'], row['rank'], row['officer_number']))}</div>
                  <div class="meta"><strong>Department:</strong> {esc(row['department'] or '-')}</div>
                  <div class="meta"><strong>Date filed:</strong> {esc(fmt_date(row['date_filed']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("**Case description**")
            st.write(row["description"] or "No description recorded.")

            linked = db.rows_to_dicts(
                db.fetch_all(
                    """
                    SELECT a.arrest_date AS "Arrest Date", a.location AS "Location",
                           o.name AS "Officer", a.notes AS "Notes"
                    FROM arrests a
                    LEFT JOIN officers o ON o.officer_id = a.officer_id
                    WHERE a.case_id = ? ORDER BY a.arrest_date
                    """,
                    (case_id,),
                )
            )
            st.markdown("**Arrests recorded on this case**")
            if linked:
                linked_frame = pd.DataFrame(linked)
                linked_frame["Arrest Date"] = linked_frame["Arrest Date"].apply(fmt_date)
                st.dataframe(linked_frame, hide_index=True, **STRETCH)
            else:
                st.caption("No arrest has been recorded against this case.")
        with detail_right:
            st.markdown("**📷 Case photograph**")
            case_photo = photo_data_uri(row["case_photo_path"])
            if case_photo:
                st.image(case_photo, width=260)
            else:
                st.info("No case photograph attached. Use ✏️ Edit Case File to add one.")

            st.markdown("**Suspect photograph**")
            photo = photo_data_uri(row["suspect_photo_path"])
            if photo:
                st.image(photo, width=200)
            else:
                st.info("No photograph on file for this suspect.")


def _case_add_tab() -> None:
    """Create a new case file."""
    suspects = suspect_choices()
    officers = officer_choices()
    if not require_records("suspects", suspects, "Add a suspect record first."):
        return
    if not require_records("officers", officers, "Add an officer record first."):
        return

    version = vkey("case_add")
    with st.form("case_add_form"):
        st.markdown("##### 🆕 New Case File")
        row1 = st.columns(2)
        case_number = row1[0].text_input(
            "Case Number *", value=suggest_case_number(), key=f"{version}_num",
            help="Automatically suggested in the OR/<year>/<serial> format.",
        )
        date_filed = row1[1].date_input("Date Filed *", value=dt.date.today(), key=f"{version}_date")

        row2 = st.columns(2)
        suspect_label = row2[0].selectbox("Suspect *", list(suspects.keys()), key=f"{version}_sus")
        officer_label = row2[1].selectbox("Investigating Officer *", list(officers.keys()), key=f"{version}_off")

        row3 = st.columns(2)
        crime_type = row3[0].selectbox("Type of Offence *", CRIME_TYPES, key=f"{version}_crime")
        status = row3[1].selectbox("Case Status *", CASE_STATUSES, key=f"{version}_status")

        description = st.text_area(
            "Brief facts of the case *",
            height=120,
            key=f"{version}_desc",
            placeholder="State the circumstances of the offence, the property involved and any "
                        "material evidence recovered...",
        )
        case_photo = st.file_uploader(
            "📷 Photograph of the case (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"{version}_photo",
            help="Attach a picture of the scene, the recovered property or the exhibit. "
                 "It is stored in photos/ and shown on the case file.",
        )
        submitted = st.form_submit_button("💾 Save Case File", type="primary", **STRETCH)

    if not submitted:
        _case_saved_panel()
        return

    if not case_number.strip():
        st.error("Case number is required.")
        return
    if len(description.strip()) < 10:
        st.error("Please enter a description of at least 10 characters.")
        return
    if db.fetch_one("SELECT case_id FROM cases WHERE case_number = ?", (case_number.strip(),)):
        st.error(f"Case number '{case_number.strip()}' already exists. Use a unique case number.")
        return

    photo_note = ""
    try:
        new_case_id = db.execute_query(
            "INSERT INTO cases (case_number, suspect_id, officer_id, crime_type, description, "
            "status, date_filed) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                case_number.strip(),
                suspects[suspect_label],
                officers[officer_label],
                crime_type,
                description.strip(),
                status,
                date_filed.isoformat(),
            ),
        )
    except sqlite3.IntegrityError as error:
        st.error(f"Could not save the case file: {error}")
        return

    # ---- attach the photograph (optional) -------------------------------- #
    if case_photo is not None:
        try:
            stored = save_case_photo(case_photo, int(new_case_id))
            if stored:
                db.execute_query("UPDATE cases SET photo_path = ? WHERE case_id = ?",
                                 (stored, int(new_case_id)))
                photo_note = " with a photograph"
        except ValueError as error:
            st.warning(f"The case was saved, but the photograph was not: {error}")

    bump("form_version_case_add")
    st.session_state["last_saved_case_id"] = int(new_case_id)
    flash("success", f"Case file {case_number.strip()} was created{photo_note} "
                     f"and now appears in the case register.")
    st.rerun()


def _case_saved_panel() -> None:
    """
    Show the case that was just created.

    Streamlit cannot programmatically switch ``st.tabs``, so after saving the
    operator stays on this tab.  That made a newly added case look as though it
    had not been recorded at all.  This panel proves it was saved, shows the
    record, and says exactly where to find it.
    """
    case_id = st.session_state.get("last_saved_case_id")
    if not case_id:
        return
    row = db.fetch_one("SELECT * FROM cases WHERE case_id = ?", (int(case_id),))
    if not row:
        return
    total = db.count_rows("cases")

    left, right = st.columns([2, 1])
    with left:
        st.success(
            f"✅ **Case file {row['case_number']} is saved.** It is now the newest entry "
            f"in the register — open the **📋 View & Search** tab above to see all "
            f"{total} case files, search it, or export it to CSV."
        )
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>🆕 {esc(row['case_number'])} — {esc(row['crime_type'])}
                  {status_pill(row['status'])}</h4>
              <div class="meta"><strong>Date filed:</strong> {esc(fmt_date(row['date_filed']))}</div>
              <div class="meta"><strong>Description:</strong>
                  {esc((row['description'] or '')[:260])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        photo = photo_data_uri(row["photo_path"])
        st.markdown("**Case photograph**")
        if photo:
            st.image(photo, width=240)
        else:
            st.info("No photograph attached to this case.")

    if st.button("✖️ Dismiss this confirmation", key="case_saved_dismiss"):
        st.session_state.pop("last_saved_case_id", None)
        st.rerun()


def _case_edit_tab() -> None:
    """Update an existing case file."""
    options = case_choices()
    if not options:
        empty_state("There are no case files to edit yet.")
        return

    label = st.selectbox("Select the case file to edit", list(options.keys()), key="case_edit_pick")
    case_id = options[label]
    row = db.fetch_one("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    if row is None:
        st.error("That case file could not be found.")
        return

    suspects = suspect_choices()
    officers = officer_choices()

    with st.form("case_edit_form"):
        st.markdown(f"##### ✏️ Editing {row['case_number']}")
        row1 = st.columns(2)
        case_number = row1[0].text_input("Case Number *", value=row["case_number"], key=f"ce_num_{case_id}")
        date_filed = row1[1].date_input(
            "Date Filed *", value=to_date(row["date_filed"]), key=f"ce_date_{case_id}"
        )
        row2 = st.columns(2)
        suspect_label = row2[0].selectbox(
            "Suspect *", list(suspects.keys()), index=index_for(suspects, row["suspect_id"]),
            key=f"ce_sus_{case_id}",
        )
        officer_label = row2[1].selectbox(
            "Investigating Officer *", list(officers.keys()), index=index_for(officers, row["officer_id"]),
            key=f"ce_off_{case_id}",
        )
        row3 = st.columns(2)
        crime_type = row3[0].selectbox(
            "Type of Offence *", CRIME_TYPES,
            index=CRIME_TYPES.index(row["crime_type"]) if row["crime_type"] in CRIME_TYPES else 0,
            key=f"ce_crime_{case_id}",
        )
        status = row3[1].selectbox(
            "Case Status *", CASE_STATUSES,
            index=CASE_STATUSES.index(row["status"]) if row["status"] in CASE_STATUSES else 0,
            key=f"ce_status_{case_id}",
        )
        description = st.text_area(
            "Brief facts of the case", value=row["description"] or "", height=120,
            key=f"ce_desc_{case_id}",
        )
        existing_photo = photo_data_uri(row["photo_path"])
        if existing_photo:
            st.markdown("**Current case photograph**")
            st.image(existing_photo, width=260)
        replace_photo = st.file_uploader(
            "📷 Replace the case photograph (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"ce_photo_{case_id}",
            help="Upload a new picture to replace the current one. "
                 "Leave empty to keep the photograph that is already attached.",
        )
        remove_photo = st.checkbox(
            "🗑️ Remove the photograph from this case",
            value=False, key=f"ce_rmphoto_{case_id}",
            disabled=not bool(row["photo_path"]),
        )
        submitted = st.form_submit_button("💾 Update Case File", type="primary", **STRETCH)

    if submitted:
        duplicate = db.fetch_one(
            "SELECT case_id FROM cases WHERE case_number = ? AND case_id <> ?",
            (case_number.strip(), case_id),
        )
        if duplicate:
            st.error("Another case file already uses that case number.")
        elif not case_number.strip():
            st.error("Case number is required.")
        else:
            db.execute_query(
                "UPDATE cases SET case_number = ?, suspect_id = ?, officer_id = ?, crime_type = ?, "
                "description = ?, status = ?, date_filed = ? WHERE case_id = ?",
                (
                    case_number.strip(),
                    suspects[suspect_label],
                    officers[officer_label],
                    crime_type,
                    description.strip(),
                    status,
                    date_filed.isoformat(),
                    case_id,
                ),
            )
            # ---- case photograph ----------------------------------------- #
            if remove_photo and row["photo_path"]:
                remove_photo_file(row["photo_path"])
                db.execute_query("UPDATE cases SET photo_path = NULL WHERE case_id = ?",
                                 (case_id,))
            if replace_photo is not None:
                try:
                    stored = save_case_photo(replace_photo, int(case_id))
                    if stored:
                        remove_photo_file(row["photo_path"])
                        db.execute_query("UPDATE cases SET photo_path = ? WHERE case_id = ?",
                                         (stored, case_id))
                except ValueError as error:
                    st.warning(f"The case was updated, but the new photograph was not saved: {error}")

            flash("success", f"Case file {case_number.strip()} was updated.")
            st.rerun()


def _case_delete_tab() -> None:
    """Delete a case file (with confirmation and cascade awareness)."""
    options = case_choices()
    if not options:
        empty_state("There are no case files to delete.")
        return

    label = st.selectbox("Select the case file to delete", list(options.keys()), key="case_del_pick")
    case_id = options[label]
    linked = db.child_counts("cases", case_id)
    if linked:
        st.warning(
            "⚠️ This case has linked records: "
            + ", ".join(f"**{t.replace('_', ' ')}** ({n})" for t, _, n in linked)
            + ". The confirmation dialog will ask whether to delete them as well."
        )
    else:
        st.info("No linked records were found for this case file.")

    if st.button("🗑️ Delete this case file", key=f"case_del_btn_{case_id}", type="primary"):
        request_delete("cases", case_id, label)


def render_cases() -> None:
    """Case file management page."""
    page_header(
        "🗂️",
        "Case Files Management",
        "Register, track and close case files opened by the Oji-River Area Command.",
    )
    if auth.is_viewer():
        readonly_notice()

    tabs = ["📋 View & Search"]
    if auth.is_admin():
        tabs += ["➕ New Case File", "✏️ Edit Case File", "🗑️ Delete Case File"]
    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _case_view_tab()
    if auth.is_admin():
        with tab_objects[1]:
            _case_add_tab()
        with tab_objects[2]:
            _case_edit_tab()
        with tab_objects[3]:
            _case_delete_tab()


# --------------------------------------------------------------------------- #
#  PAGE: Arrest records
# --------------------------------------------------------------------------- #
def _arrest_view_tab() -> None:
    """Searchable arrest register with detail view."""
    filter_a, filter_b = st.columns([2, 1])
    search = filter_a.text_input(
        "🔍 Search arrest records",
        placeholder="Suspect, officer, case number, location or notes...",
        key="arrest_search",
    )
    locations = filter_b.multiselect("Filter by location", LOCATIONS, key="arrest_loc_filter")

    frame = arrests_frame(search, locations)
    if frame.empty:
        empty_state("No arrest record matches the current filter.", "🚔")
        return

    st.caption(f"📌 {len(frame)} arrest record(s) displayed.")
    st.dataframe(frame, hide_index=True, height=360, **STRETCH)
    download_csv(frame, "arrest_records.csv")

    st.markdown("#### 🔎 Full arrest details")
    rows = db.fetch_all(
        """
        SELECT a.arrest_id, a.arrest_date, a.location, a.notes,
               s.name AS suspect_name, s.sex, s.address, s.occupation, s.photo_path,
               o.name AS officer_name, o.officer_number, o.rank, o.department,
               c.case_number, c.crime_type, c.status
        FROM arrests a
        LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
        LEFT JOIN officers o ON o.officer_id = a.officer_id
        LEFT JOIN cases c ON c.case_id = a.case_id
        ORDER BY a.arrest_date DESC
        """
    )
    if not rows:
        return
    labels = {
        f"ARR-{int(r['arrest_id']):03d} | {r['suspect_name'] or 'Not recorded'} - "
        f"{fmt_date(r['arrest_date'])} @ {r['location']}": int(r["arrest_id"])
        for r in rows
    }
    chosen = st.selectbox("Select an arrest record to inspect", list(labels.keys()), key="arrest_detail_pick")
    target = labels[chosen]
    record = next((r for r in rows if int(r["arrest_id"]) == target), None)
    if record is None:
        return

    detail_left, detail_right = st.columns([2.2, 1])
    with detail_left:
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>Arrest of {esc(record['suspect_name'] or 'Not recorded')}</h4>
              <div class="meta"><strong>Arrest date:</strong> {esc(fmt_date(record['arrest_date']))}</div>
              <div class="meta"><strong>Location:</strong> {esc(record['location'])}</div>
              <div class="meta"><strong>Arresting officer:</strong>
                  {esc(officer_display(record['officer_name'], record['rank'], record['officer_number']))}</div>
              <div class="meta"><strong>Department:</strong> {esc(record['department'] or '-')}</div>
              <div class="meta"><strong>Linked case:</strong>
                  {esc(record['case_number'] or 'Not linked')}
                  {status_pill(record['status']) if record['status'] else ''}</div>
              <div class="meta"><strong>Offence:</strong> {esc(record['crime_type'] or '-')}</div>
              <div class="meta"><strong>Suspect address:</strong> {esc(record['address'] or '-')}</div>
              <div class="meta"><strong>Occupation:</strong> {esc(record['occupation'] or '-')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("**Arrest notes**")
        st.write(record["notes"] or "No notes recorded.")
    with detail_right:
        photo = photo_data_uri(record["photo_path"])
        st.markdown("**Suspect photograph**")
        if photo:
            st.image(photo, width=220)
        else:
            st.info("No photograph on file.")


def _arrest_add_tab() -> None:
    """Record a new arrest."""
    suspects = suspect_choices()
    officers = officer_choices(include_blank=True)
    cases = case_choices(include_blank=True)
    if not require_records("suspects", suspects, "Add a suspect record first."):
        return

    version = vkey("arrest_add")
    with st.form("arrest_add_form"):
        st.markdown("##### 🆕 New Arrest Record")
        row1 = st.columns(2)
        suspect_label = row1[0].selectbox("Suspect *", list(suspects.keys()), key=f"{version}_sus")
        officer_label = row1[1].selectbox("Arresting Officer *", list(officers.keys()), key=f"{version}_off")

        row2 = st.columns(2)
        case_label = row2[0].selectbox(
            "Linked Case File", list(cases.keys()), key=f"{version}_case",
            help="An arrest may be recorded before a case file is opened.",
        )
        arrest_date = row2[1].date_input("Arrest Date *", value=dt.date.today(), key=f"{version}_date")

        venue = st.selectbox(
            "Location of Arrest *", LOCATIONS + ["Other (specify below)"], key=f"{version}_loc"
        )
        other_venue = st.text_input(
            "Specify location", key=f"{version}_other",
            placeholder="Only required when 'Other' is selected above.",
        )
        notes = st.text_area(
            "Arrest notes", height=110, key=f"{version}_notes",
            placeholder="Circumstances of the arrest, exhibits recovered, cautionary words...",
        )
        submitted = st.form_submit_button("💾 Save Arrest Record", type="primary", **STRETCH)

    if not submitted:
        return

    location = other_venue.strip() if venue.startswith("Other") else venue
    if not location:
        st.error("Please state the location of the arrest.")
        return

    db.execute_query(
        "INSERT INTO arrests (suspect_id, officer_id, case_id, arrest_date, location, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            suspects[suspect_label],
            officers[officer_label],
            cases[case_label],
            arrest_date.isoformat(),
            location,
            notes.strip(),
        ),
    )
    bump("form_version_arrest_add")
    flash("success", "Arrest record saved successfully.")
    st.rerun()


def _arrest_edit_tab() -> None:
    """Update an existing arrest record."""
    rows = db.fetch_all(
        """
        SELECT a.*, s.name AS suspect_name, c.case_number
        FROM arrests a
        LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
        LEFT JOIN cases c ON c.case_id = a.case_id
        ORDER BY a.arrest_date DESC
        """
    )
    if not rows:
        empty_state("There are no arrest records to edit yet.")
        return

    labels = {
        f"ARR-{int(r['arrest_id']):03d} | {r['suspect_name'] or 'Not recorded'} - "
        f"{fmt_date(r['arrest_date'])} @ {r['location']}": int(r["arrest_id"])
        for r in rows
    }
    chosen = st.selectbox("Select the arrest record to edit", list(labels.keys()), key="arrest_edit_pick")
    arrest_id = labels[chosen]
    record = db.fetch_one("SELECT * FROM arrests WHERE arrest_id = ?", (arrest_id,))
    if record is None:
        st.error("That arrest record could not be found.")
        return

    suspects = suspect_choices()
    officers = officer_choices(include_blank=True)
    cases = case_choices(include_blank=True)

    with st.form("arrest_edit_form"):
        st.markdown(f"##### ✏️ Editing arrest record ARR-{arrest_id:03d}")
        row1 = st.columns(2)
        suspect_label = row1[0].selectbox(
            "Suspect *", list(suspects.keys()), index=index_for(suspects, record["suspect_id"]),
            key=f"ae_sus_{arrest_id}",
        )
        officer_label = row1[1].selectbox(
            "Arresting Officer", list(officers.keys()), index=index_for(officers, record["officer_id"]),
            key=f"ae_off_{arrest_id}",
        )
        row2 = st.columns(2)
        case_label = row2[0].selectbox(
            "Linked Case File", list(cases.keys()), index=index_for(cases, record["case_id"]),
            key=f"ae_case_{arrest_id}",
        )
        arrest_date = row2[1].date_input(
            "Arrest Date *", value=to_date(record["arrest_date"]), key=f"ae_date_{arrest_id}"
        )
        location = st.text_input("Location of Arrest *", value=record["location"], key=f"ae_loc_{arrest_id}")
        notes = st.text_area("Arrest notes", value=record["notes"] or "", height=110, key=f"ae_notes_{arrest_id}")
        submitted = st.form_submit_button("💾 Update Arrest Record", type="primary", **STRETCH)

    if submitted:
        if not location.strip():
            st.error("Location of arrest is required.")
        else:
            db.execute_query(
                "UPDATE arrests SET suspect_id = ?, officer_id = ?, case_id = ?, arrest_date = ?, "
                "location = ?, notes = ? WHERE arrest_id = ?",
                (
                    suspects[suspect_label],
                    officers[officer_label],
                    cases[case_label],
                    arrest_date.isoformat(),
                    location.strip(),
                    notes.strip(),
                    arrest_id,
                ),
            )
            flash("success", f"Arrest record ARR-{arrest_id:03d} was updated.")
            st.rerun()


def _arrest_delete_tab() -> None:
    """Delete an arrest record."""
    rows = db.fetch_all(
        """
        SELECT a.arrest_id, a.arrest_date, a.location, s.name AS suspect_name
        FROM arrests a LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
        ORDER BY a.arrest_date DESC
        """
    )
    if not rows:
        empty_state("There are no arrest records to delete.")
        return
    labels = {
        f"ARR-{int(r['arrest_id']):03d} | {r['suspect_name'] or 'Not recorded'} - "
        f"{fmt_date(r['arrest_date'])} @ {r['location']}": int(r["arrest_id"])
        for r in rows
    }
    chosen = st.selectbox("Select the arrest record to delete", list(labels.keys()), key="arrest_del_pick")
    arrest_id = labels[chosen]
    st.info("Arrest records are not referenced by any other table, so deletion is straightforward.")
    if st.button("🗑️ Delete this arrest record", key=f"arrest_del_btn_{arrest_id}", type="primary"):
        request_delete("arrests", arrest_id, chosen)


def render_arrests() -> None:
    """Arrest record management page."""
    page_header(
        "🚔",
        "Arrest Records Management",
        "Capture arrests effected by the command and link them to case files and suspects.",
    )
    if auth.is_viewer():
        readonly_notice()

    tabs = ["📋 View & Search"]
    if auth.is_admin():
        tabs += ["➕ New Arrest", "✏️ Edit Arrest", "🗑️ Delete Arrest"]
    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _arrest_view_tab()
    if auth.is_admin():
        with tab_objects[1]:
            _arrest_add_tab()
        with tab_objects[2]:
            _arrest_edit_tab()
        with tab_objects[3]:
            _arrest_delete_tab()


# --------------------------------------------------------------------------- #
#  PAGE: Wanted persons
# --------------------------------------------------------------------------- #
def _wanted_cards(frame: pd.DataFrame) -> None:
    """Render the wanted register as photograph cards."""
    for record in frame.to_dict("records"):
        left, middle, right = st.columns([1, 3, 1.2])
        with left:
            photo = photo_data_uri(record.get("photo_path"))
            if photo:
                st.image(photo, width=150)
            else:
                st.markdown(
                    "<div style='height:150px;border:1px dashed #b9c2cc;border-radius:8px;"
                    "display:flex;align-items:center;justify-content:center;color:#7b8794;"
                    "font-size:.8rem;text-align:center;'>NO PHOTOGRAPH<br/>ON FILE</div>",
                    unsafe_allow_html=True,
                )
        with middle:
            st.markdown(
                f"""
                <div class="npf-card">
                  <h4>{esc(record['Suspect'])} &nbsp; {status_pill(record['Status'])}</h4>
                  <div class="meta"><strong>Offence:</strong> {esc(record['Offence'])}</div>
                  <div class="meta"><strong>Reward offered:</strong> {esc(record['Reward (NGN)'])}</div>
                  <div class="meta"><strong>Last seen:</strong> {esc(record['Last Seen Location'])}</div>
                  <div class="meta"><strong>Sex:</strong> {esc(SEX_LABELS.get(record['Sex'], record['Sex']))}
                      &nbsp;|&nbsp; <strong>Entry added:</strong> {esc(record['Date Added'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            wanted_id = int(record["wanted_id"])
            if auth.is_admin():
                if record["Status"] == "At Large":
                    if st.button("✅ Mark as Captured", key=f"cap_{wanted_id}", **STRETCH):
                        db.execute_query(
                            "UPDATE wanted_persons SET status = 'Captured' WHERE wanted_id = ?",
                            (wanted_id,),
                        )
                        flash("success", f"{record['Suspect']} has been marked as captured.")
                        st.rerun()
                else:
                    if st.button("↩️ Return to At Large", key=f"rel_{wanted_id}", **STRETCH):
                        db.execute_query(
                            "UPDATE wanted_persons SET status = 'At Large' WHERE wanted_id = ?",
                            (wanted_id,),
                        )
                        flash("success", f"{record['Suspect']} has been returned to the wanted list.")
                        st.rerun()
                if st.button("🗑️ Remove from list", key=f"wdel_{wanted_id}", **STRETCH):
                    request_delete(
                        "wanted_persons", wanted_id, f"{record['Suspect']} — {record['Offence']}"
                    )
            else:
                st.caption("Status changes require an Administrator.")


def _wanted_view_tab() -> None:
    """Wanted register with notification-style cards."""
    filter_a, filter_b = st.columns([2, 1])
    search = filter_a.text_input(
        "🔍 Search wanted persons",
        placeholder="Suspect name, offence or last seen location...",
        key="wanted_search",
    )
    statuses = filter_b.multiselect("Filter by status", WANTED_STATUSES, key="wanted_status_filter")

    frame = wanted_frame(search, statuses)
    if frame.empty:
        empty_state("No wanted person matches the current filter.", "🎯")
        return

    st.caption(f"📌 {len(frame)} wanted person(s) on the register.")
    _wanted_cards(frame)

    st.markdown("#### 📋 Tabular view")
    table = frame.drop(columns=["wanted_id", "photo_path"])
    st.dataframe(table, hide_index=True, **STRETCH)
    download_csv(table, "wanted_persons.csv")


def _wanted_add_tab() -> None:
    """Add a suspect to the wanted register."""
    suspects = suspect_choices()
    if not require_records("suspects", suspects, "Add a suspect record first."):
        return

    version = vkey("wanted_add")
    with st.form("wanted_add_form"):
        st.markdown("##### 🆕 Add to the Wanted Register")
        row1 = st.columns(2)
        suspect_label = row1[0].selectbox("Suspect *", list(suspects.keys()), key=f"{version}_sus")
        crime_type = row1[1].selectbox("Offence *", CRIME_TYPES, key=f"{version}_crime")
        row2 = st.columns(2)
        reward = row2[0].number_input(
            "Reward offered (NGN)", min_value=0.0, step=50_000.0, value=200_000.0,
            key=f"{version}_reward",
        )
        status = row2[1].selectbox("Status *", WANTED_STATUSES, key=f"{version}_status")
        last_seen = st.text_input(
            "Last seen location *", key=f"{version}_last",
            placeholder="e.g. Udi main market, Udi LGA, Enugu State",
        )
        submitted = st.form_submit_button("💾 Add to Wanted List", type="primary", **STRETCH)

    if not submitted:
        return
    if not last_seen.strip():
        st.error("Please state where the suspect was last seen.")
        return

    db.execute_query(
        "INSERT INTO wanted_persons (suspect_id, crime_type, reward_amount, last_seen, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (suspects[suspect_label], crime_type, float(reward), last_seen.strip(), status),
    )
    bump("form_version_wanted_add")
    flash("success", "Suspect added to the wanted register.")
    st.rerun()


def _wanted_edit_tab() -> None:
    """Edit a wanted register entry."""
    rows = db.fetch_all(
        """
        SELECT w.*, s.name AS suspect_name
        FROM wanted_persons w LEFT JOIN suspects s ON s.suspect_id = w.suspect_id
        ORDER BY w.date_added DESC
        """
    )
    if not rows:
        empty_state("The wanted register is empty.")
        return
    labels = {
        f"WAN-{int(r['wanted_id']):03d} | {r['suspect_name'] or 'Not recorded'} - "
        f"{r['crime_type']} [{r['status']}]": int(r["wanted_id"])
        for r in rows
    }
    chosen = st.selectbox("Select the wanted entry to edit", list(labels.keys()), key="wanted_edit_pick")
    wanted_id = labels[chosen]
    record = db.fetch_one("SELECT * FROM wanted_persons WHERE wanted_id = ?", (wanted_id,))
    if record is None:
        st.error("That entry could not be found.")
        return

    suspects = suspect_choices()
    with st.form("wanted_edit_form"):
        st.markdown(f"##### ✏️ Editing wanted entry WAN-{wanted_id:03d}")
        row1 = st.columns(2)
        suspect_label = row1[0].selectbox(
            "Suspect *", list(suspects.keys()), index=index_for(suspects, record["suspect_id"]),
            key=f"we_sus_{wanted_id}",
        )
        crime_type = row1[1].selectbox(
            "Offence *", CRIME_TYPES,
            index=CRIME_TYPES.index(record["crime_type"]) if record["crime_type"] in CRIME_TYPES else 0,
            key=f"we_crime_{wanted_id}",
        )
        row2 = st.columns(2)
        reward = row2[0].number_input(
            "Reward offered (NGN)", min_value=0.0, step=50_000.0,
            value=float(record["reward_amount"] or 0.0), key=f"we_reward_{wanted_id}",
        )
        status = row2[1].selectbox(
            "Status *", WANTED_STATUSES,
            index=WANTED_STATUSES.index(record["status"]) if record["status"] in WANTED_STATUSES else 0,
            key=f"we_status_{wanted_id}",
        )
        last_seen = st.text_input(
            "Last seen location *", value=record["last_seen"] or "", key=f"we_last_{wanted_id}"
        )
        submitted = st.form_submit_button("💾 Update Wanted Entry", type="primary", **STRETCH)

    if submitted:
        db.execute_query(
            "UPDATE wanted_persons SET suspect_id = ?, crime_type = ?, reward_amount = ?, "
            "last_seen = ?, status = ? WHERE wanted_id = ?",
            (
                suspects[suspect_label],
                crime_type,
                float(reward),
                last_seen.strip(),
                status,
                wanted_id,
            ),
        )
        flash("success", f"Wanted entry WAN-{wanted_id:03d} was updated.")
        st.rerun()


def _wanted_delete_tab() -> None:
    """Delete a wanted register entry."""
    rows = db.fetch_all(
        """
        SELECT w.wanted_id, w.crime_type, w.status, s.name AS suspect_name
        FROM wanted_persons w LEFT JOIN suspects s ON s.suspect_id = w.suspect_id
        ORDER BY w.date_added DESC
        """
    )
    if not rows:
        empty_state("The wanted register is empty.")
        return
    labels = {
        f"WAN-{int(r['wanted_id']):03d} | {r['suspect_name'] or 'Not recorded'} - "
        f"{r['crime_type']} [{r['status']}]": int(r["wanted_id"])
        for r in rows
    }
    chosen = st.selectbox("Select the wanted entry to delete", list(labels.keys()), key="wanted_del_pick")
    wanted_id = labels[chosen]
    if st.button("🗑️ Delete this wanted entry", key=f"wanted_del_btn_{wanted_id}", type="primary"):
        request_delete("wanted_persons", wanted_id, chosen)


def render_wanted() -> None:
    """Wanted persons page."""
    page_header(
        "🎯",
        "Wanted Persons Register",
        "Suspects declared wanted by the command, with photographs and rewards offered.",
    )
    if auth.is_viewer():
        readonly_notice()

    tabs = ["📋 Register & Search"]
    if auth.is_admin():
        tabs += ["➕ Add Wanted Person", "✏️ Edit Entry", "🗑️ Delete Entry"]
    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _wanted_view_tab()
    if auth.is_admin():
        with tab_objects[1]:
            _wanted_add_tab()
        with tab_objects[2]:
            _wanted_edit_tab()
        with tab_objects[3]:
            _wanted_delete_tab()


# --------------------------------------------------------------------------- #
#  PAGE: Officers
# --------------------------------------------------------------------------- #
def _officer_view_tab() -> None:
    """Personnel register with caseload analysis."""
    filter_a, filter_b = st.columns([2, 1])
    search = filter_a.text_input(
        "🔍 Search officers",
        placeholder="Name, officer number, rank or department...",
        key="officer_search",
    )
    departments = filter_b.multiselect("Filter by department", DEPARTMENTS, key="officer_dept_filter")

    frame = officers_frame(search, departments)
    if frame.empty:
        empty_state("No officer matches the current filter.", "👮")
        return

    st.caption(f"📌 {len(frame)} officer(s) displayed.")
    st.dataframe(frame, hide_index=True, height=340, **STRETCH)
    download_csv(frame, "officers.csv")

    st.markdown("#### 📂 Cases handled by each officer")
    rows = db.fetch_all("SELECT officer_id, name, rank, officer_number FROM officers ORDER BY name")
    if not rows:
        return
    labels = {
        f"OFF-{int(r['officer_id']):03d} | {RANK_ABBR.get(r['rank'], r['rank'])} {r['name']} "
        f"(No. {r['officer_number']})": int(r["officer_id"])
        for r in rows
    }
    chosen = st.selectbox("Select an officer", list(labels.keys()), key="officer_detail_pick")
    officer_id = labels[chosen]

    summary = db.fetch_one(
        """
        SELECT o.name, o.rank, o.officer_number, o.department, o.date_joined,
               (SELECT COUNT(*) FROM cases c WHERE c.officer_id = o.officer_id) AS cases_handled,
               (SELECT COUNT(*) FROM cases c WHERE c.officer_id = o.officer_id
                  AND c.status IN ('Open','Under Investigation')) AS active_cases,
               (SELECT COUNT(*) FROM arrests a WHERE a.officer_id = o.officer_id) AS arrests
        FROM officers o WHERE o.officer_id = ?
        """,
        (officer_id,),
    )
    if summary is None:
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("📂 Cases Handled", summary["cases_handled"])
    metric_cols[1].metric("🔥 Active Files", summary["active_cases"])
    metric_cols[2].metric("🚔 Arrests Effected", summary["arrests"])
    metric_cols[3].metric("🏛️ Department", summary["department"])

    st.markdown(
        f"**{esc(officer_display(summary['name'], summary['rank'], summary['officer_number']))}** "
        f"— joined the command on {esc(fmt_date(summary['date_joined']))}."
    )

    cases = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT c.case_number AS "Case Number", c.crime_type AS "Offence",
                   COALESCE(s.name, 'Not recorded') AS "Suspect",
                   c.status AS "Status", c.date_filed AS "Date Filed"
            FROM cases c
            LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
            WHERE c.officer_id = ?
            ORDER BY c.date_filed DESC
            """,
            (officer_id,),
        )
    )
    if cases:
        case_frame = pd.DataFrame(cases)
        case_frame["Date Filed"] = case_frame["Date Filed"].apply(fmt_date)
        st.dataframe(case_frame, hide_index=True, **STRETCH)
    else:
        st.caption("This officer has not been assigned any case file yet.")

    arrests = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT a.arrest_date AS "Arrest Date", COALESCE(s.name, 'Not recorded') AS "Suspect",
                   a.location AS "Location", COALESCE(c.case_number, 'Not linked') AS "Case Number"
            FROM arrests a
            LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
            LEFT JOIN cases c ON c.case_id = a.case_id
            WHERE a.officer_id = ?
            ORDER BY a.arrest_date DESC
            """,
            (officer_id,),
        )
    )
    if arrests:
        st.markdown("**Arrests effected by this officer**")
        arrest_frame = pd.DataFrame(arrests)
        arrest_frame["Arrest Date"] = arrest_frame["Arrest Date"].apply(fmt_date)
        st.dataframe(arrest_frame, hide_index=True, **STRETCH)


def _officer_add_tab() -> None:
    """Register a new officer."""
    version = vkey("officer_add")
    with st.form("officer_add_form"):
        st.markdown("##### 🆕 New Officer Record")
        row1 = st.columns(2)
        officer_number = row1[0].text_input(
            "Officer Number *", key=f"{version}_num",
            placeholder="Format: 0785129",
            help="The force number printed on the officer's identity card.",
        )
        name = row1[1].text_input("Full Name *", key=f"{version}_name", placeholder="Surname First Other Names")
        row2 = st.columns(2)
        rank = row2[0].selectbox("Rank *", RANKS, key=f"{version}_rank")
        department = row2[1].selectbox("Department *", DEPARTMENTS, key=f"{version}_dept")
        date_joined = st.date_input("Date Joined *", value=dt.date.today(), key=f"{version}_joined")
        submitted = st.form_submit_button("💾 Save Officer", type="primary", **STRETCH)

    if not submitted:
        return
    if not officer_number.strip() or not name.strip():
        st.error("Officer number and full name are required.")
        return
    if db.fetch_one("SELECT officer_id FROM officers WHERE officer_number = ?", (officer_number.strip(),)):
        st.error(f"Officer number {officer_number.strip()} is already on the register.")
        return

    db.execute_query(
        "INSERT INTO officers (officer_number, name, rank, department, date_joined) "
        "VALUES (?, ?, ?, ?, ?)",
        (officer_number.strip(), name.strip(), rank, department, date_joined.isoformat()),
    )
    bump("form_version_officer_add")
    flash("success", f"Officer {name.strip()} ({officer_number.strip()}) was added to the register.")
    st.rerun()


def _officer_edit_tab() -> None:
    """Update an officer record."""
    options = officer_choices()
    if not options:
        empty_state("There are no officer records to edit yet.")
        return
    label = st.selectbox("Select the officer to edit", list(options.keys()), key="officer_edit_pick")
    officer_id = options[label]
    record = db.fetch_one("SELECT * FROM officers WHERE officer_id = ?", (officer_id,))
    if record is None:
        st.error("That officer record could not be found.")
        return

    with st.form("officer_edit_form"):
        st.markdown(f"##### ✏️ Editing OFF-{officer_id:03d}")
        row1 = st.columns(2)
        officer_number = row1[0].text_input(
            "Officer Number *", value=record["officer_number"], key=f"oe_num_{officer_id}"
        )
        name = row1[1].text_input("Full Name *", value=record["name"], key=f"oe_name_{officer_id}")
        row2 = st.columns(2)
        rank = row2[0].selectbox(
            "Rank *", RANKS,
            index=RANKS.index(record["rank"]) if record["rank"] in RANKS else 0,
            key=f"oe_rank_{officer_id}",
        )
        department = row2[1].selectbox(
            "Department *", DEPARTMENTS,
            index=DEPARTMENTS.index(record["department"]) if record["department"] in DEPARTMENTS else 0,
            key=f"oe_dept_{officer_id}",
        )
        date_joined = st.date_input(
            "Date Joined *", value=to_date(record["date_joined"]), key=f"oe_joined_{officer_id}"
        )
        submitted = st.form_submit_button("💾 Update Officer", type="primary", **STRETCH)

    if submitted:
        duplicate = db.fetch_one(
            "SELECT officer_id FROM officers WHERE officer_number = ? AND officer_id <> ?",
            (officer_number.strip(), officer_id),
        )
        if duplicate:
            st.error("Another officer already has that officer number.")
        elif not name.strip():
            st.error("Full name is required.")
        else:
            db.execute_query(
                "UPDATE officers SET officer_number = ?, name = ?, rank = ?, department = ?, "
                "date_joined = ? WHERE officer_id = ?",
                (
                    officer_number.strip(),
                    name.strip(),
                    rank,
                    department,
                    date_joined.isoformat(),
                    officer_id,
                ),
            )
            flash("success", f"Officer record OFF-{officer_id:03d} was updated.")
            st.rerun()


def _officer_delete_tab() -> None:
    """Delete an officer record."""
    options = officer_choices()
    if not options:
        empty_state("There are no officer records to delete.")
        return
    label = st.selectbox("Select the officer to delete", list(options.keys()), key="officer_del_pick")
    officer_id = options[label]
    linked = db.child_counts("officers", officer_id)
    if linked:
        st.warning(
            "⚠️ This officer is referenced by: "
            + ", ".join(f"**{t.replace('_', ' ')}** ({n})" for t, _, n in linked)
            + ". Reassign those records first, or use the cascade option in the dialog."
        )
    if st.button("🗑️ Delete this officer record", key=f"officer_del_btn_{officer_id}", type="primary"):
        request_delete("officers", officer_id, label)


def render_officers() -> None:
    """Officers / personnel page."""
    page_header(
        "👮",
        "Officers and Personnel",
        "Personnel of the Oji-River Area Command and the case files assigned to each officer.",
    )
    if auth.is_viewer():
        readonly_notice()

    tabs = ["📋 Register & Caseload"]
    if auth.is_admin():
        tabs += ["➕ Add Officer", "✏️ Edit Officer", "🗑️ Delete Officer"]
    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _officer_view_tab()
    if auth.is_admin():
        with tab_objects[1]:
            _officer_add_tab()
        with tab_objects[2]:
            _officer_edit_tab()
        with tab_objects[3]:
            _officer_delete_tab()


# --------------------------------------------------------------------------- #
#  PAGE: Suspects
# --------------------------------------------------------------------------- #
def _suspect_view_tab() -> None:
    """Suspect register with photographs."""
    filter_a, filter_b = st.columns([2, 1])
    search = filter_a.text_input(
        "🔍 Search suspects",
        placeholder="Name, address or occupation...",
        key="suspect_search",
    )
    sexes = filter_b.multiselect("Filter by sex", SEXES, key="suspect_sex_filter")

    frame = suspects_frame(search, sexes)
    if frame.empty:
        empty_state("No suspect record matches the current filter.", "🧾")
        return

    st.caption(f"📌 {len(frame)} suspect(s) displayed.")
    table = frame.drop(columns=["suspect_id", "photo_path"]).copy()
    table.insert(0, "Photo", frame["photo_path"].apply(photo_data_uri))

    try:
        st.dataframe(
            table,
            hide_index=True,
            height=340,
            column_config={
                "Photo": st.column_config.ImageColumn("Photograph", width="small"),
                "Cases": st.column_config.NumberColumn("Cases", width="small"),
                "Arrests": st.column_config.NumberColumn("Arrests", width="small"),
            },
            **STRETCH,
        )
    except Exception:  # pragma: no cover - very old Streamlit without ImageColumn
        st.dataframe(table.drop(columns=["Photo"]), hide_index=True, **STRETCH)

    download_csv(table.drop(columns=["Photo"]), "suspects.csv")

    st.markdown("#### 🖼️ Suspect photograph gallery")
    gallery = st.columns(4)
    for position, record in enumerate(frame.to_dict("records")):
        column = gallery[position % 4]
        with column:
            photo = photo_data_uri(record["photo_path"])
            if photo:
                st.image(photo, width=160)
            else:
                st.markdown(
                    "<div style='height:160px;border:1px dashed #b9c2cc;border-radius:8px;"
                    "display:flex;align-items:center;justify-content:center;color:#7b8794;"
                    "font-size:.75rem;text-align:center;'>NO PHOTOGRAPH</div>",
                    unsafe_allow_html=True,
                )
            st.caption(f"**{record['Name']}**  \n{record['Sex']}, {record['Age']} yrs  \n{record['Occupation']}")

    st.markdown("#### 🔎 Full suspect details")
    options = suspect_choices()
    label = st.selectbox("Select a suspect to inspect", list(options.keys()), key="suspect_detail_pick")
    suspect_id = options[label]
    record = db.fetch_one("SELECT * FROM suspects WHERE suspect_id = ?", (suspect_id,))
    if record is None:
        return

    detail_left, detail_right = st.columns([2.2, 1])
    with detail_left:
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>{esc(record['name'])}</h4>
              <div class="meta"><strong>Sex:</strong> {esc(SEX_LABELS.get(record['sex'], record['sex']))}
                  &nbsp;|&nbsp; <strong>Age:</strong> {esc(record['age'] or '-')}
                  &nbsp;|&nbsp; <strong>Height:</strong> {esc(record['height'] or '-')}</div>
              <div class="meta"><strong>Address:</strong> {esc(record['address'] or '-')}</div>
              <div class="meta"><strong>Occupation:</strong> {esc(record['occupation'] or '-')}</div>
              <div class="meta"><strong>Record created:</strong> {esc(fmt_stamp(record['date_added']))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cases = db.rows_to_dicts(
            db.fetch_all(
                """
                SELECT c.case_number AS "Case Number", c.crime_type AS "Offence",
                       c.status AS "Status", c.date_filed AS "Date Filed"
                FROM cases c WHERE c.suspect_id = ? ORDER BY c.date_filed DESC
                """,
                (suspect_id,),
            )
        )
        st.markdown("**Case files involving this suspect**")
        if cases:
            case_frame = pd.DataFrame(cases)
            case_frame["Date Filed"] = case_frame["Date Filed"].apply(fmt_date)
            st.dataframe(case_frame, hide_index=True, **STRETCH)
        else:
            st.caption("No case file has been opened against this suspect.")

        wanted = db.fetch_one(
            "SELECT status, crime_type, reward_amount FROM wanted_persons WHERE suspect_id = ?",
            (suspect_id,),
        )
        if wanted:
            st.markdown(
                f"**Wanted register:** {status_pill(wanted['status'])} for {esc(wanted['crime_type'])} "
                f"— reward {esc(naira(wanted['reward_amount']))}"
            )
    with detail_right:
        photo = photo_data_uri(record["photo_path"])
        st.markdown("**Photograph**")
        if photo:
            st.image(photo, width=240)
        else:
            st.info("No photograph on file.")


def _suspect_add_tab() -> None:
    """Register a new suspect, optionally with a photograph."""
    version = vkey("suspect_add")
    with st.form("suspect_add_form"):
        st.markdown("##### 🆕 New Suspect Record")
        row1 = st.columns(2)
        name = row1[0].text_input("Full Name *", key=f"{version}_name")
        sex = row1[1].selectbox("Sex *", SEXES, format_func=lambda s: SEX_LABELS.get(s, s), key=f"{version}_sex")
        row2 = st.columns(2)
        age = row2[0].number_input("Age", min_value=0, max_value=120, value=30, step=1, key=f"{version}_age")
        height = row2[1].text_input("Height", key=f"{version}_height", placeholder="e.g. 1.72 m")
        address = st.text_input("Residential Address", key=f"{version}_address")
        occupation = st.text_input("Occupation", key=f"{version}_occupation")
        photo = st.file_uploader(
            "Suspect photograph", type=["jpg", "jpeg", "png", "webp"], key=f"{version}_photo",
            help="The image is resized and stored in the photos/ folder.",
        )
        submitted = st.form_submit_button("💾 Save Suspect", type="primary", **STRETCH)

    if not submitted:
        return
    if not name.strip():
        st.error("The suspect's full name is required.")
        return

    try:
        suspect_id = db.execute_query(
            "INSERT INTO suspects (name, sex, address, occupation, age, height, photo_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name.strip(),
                sex,
                address.strip(),
                occupation.strip(),
                int(age) if age else None,
                height.strip(),
                None,
            ),
        )
        if photo is not None:
            stored = save_suspect_photo(photo, int(suspect_id))
            if stored:
                db.execute_query(
                    "UPDATE suspects SET photo_path = ? WHERE suspect_id = ?", (stored, int(suspect_id))
                )
    except ValueError as error:
        db.execute_query("DELETE FROM suspects WHERE suspect_id = ?", (int(suspect_id),))
        st.error(f"Photograph could not be processed: {error}")
        return
    except Exception as error:
        st.error(f"Could not save the suspect record: {error}")
        return

    bump("form_version_suspect_add")
    flash("success", f"Suspect {name.strip()} was added with record number SUS-{int(suspect_id):03d}.")
    st.rerun()


def _suspect_edit_tab() -> None:
    """Update a suspect record and optionally replace the photograph."""
    options = suspect_choices()
    if not options:
        empty_state("There are no suspect records to edit yet.")
        return
    label = st.selectbox("Select the suspect to edit", list(options.keys()), key="suspect_edit_pick")
    suspect_id = options[label]
    record = db.fetch_one("SELECT * FROM suspects WHERE suspect_id = ?", (suspect_id,))
    if record is None:
        st.error("That suspect record could not be found.")
        return

    photo_col, form_col = st.columns([1, 3])
    with photo_col:
        st.markdown("**Current photograph**")
        photo = photo_data_uri(record["photo_path"])
        if photo:
            st.image(photo, width=200)
        else:
            st.info("No photograph on file.")

    with form_col:
        with st.form("suspect_edit_form"):
            st.markdown(f"##### ✏️ Editing SUS-{suspect_id:03d}")
            row1 = st.columns(2)
            name = row1[0].text_input("Full Name *", value=record["name"], key=f"se_name_{suspect_id}")
            sex = row1[1].selectbox(
                "Sex *", SEXES, index=SEXES.index(record["sex"]) if record["sex"] in SEXES else 0,
                format_func=lambda s: SEX_LABELS.get(s, s), key=f"se_sex_{suspect_id}",
            )
            row2 = st.columns(2)
            age = row2[0].number_input(
                "Age", min_value=0, max_value=120, value=int(record["age"] or 0), step=1,
                key=f"se_age_{suspect_id}",
            )
            height = row2[1].text_input("Height", value=record["height"] or "", key=f"se_height_{suspect_id}")
            address = st.text_input("Residential Address", value=record["address"] or "", key=f"se_addr_{suspect_id}")
            occupation = st.text_input(
                "Occupation", value=record["occupation"] or "", key=f"se_occ_{suspect_id}"
            )
            new_photo = st.file_uploader(
                "Replace photograph (optional)", type=["jpg", "jpeg", "png", "webp"],
                key=f"se_photo_{suspect_id}",
            )
            remove_photo = st.checkbox(
                "Remove the existing photograph", value=False, key=f"se_rmphoto_{suspect_id}"
            )
            submitted = st.form_submit_button("💾 Update Suspect", type="primary", **STRETCH)

    if not submitted:
        return
    if not name.strip():
        st.error("The suspect's full name is required.")
        return

    stored_path = record["photo_path"]
    try:
        if new_photo is not None:
            stored_path = save_suspect_photo(new_photo, suspect_id)
            if record["photo_path"]:
                remove_photo_file(record["photo_path"])
        elif remove_photo and record["photo_path"]:
            remove_photo_file(record["photo_path"])
            stored_path = None
    except ValueError as error:
        st.error(f"Photograph could not be processed: {error}")
        return

    db.execute_query(
        "UPDATE suspects SET name = ?, sex = ?, address = ?, occupation = ?, age = ?, "
        "height = ?, photo_path = ? WHERE suspect_id = ?",
        (
            name.strip(),
            sex,
            address.strip(),
            occupation.strip(),
            int(age) if age else None,
            height.strip(),
            stored_path,
            suspect_id,
        ),
    )
    flash("success", f"Suspect record SUS-{suspect_id:03d} was updated.")
    st.rerun()


def _suspect_delete_tab() -> None:
    """Delete a suspect record."""
    options = suspect_choices()
    if not options:
        empty_state("There are no suspect records to delete.")
        return
    label = st.selectbox("Select the suspect to delete", list(options.keys()), key="suspect_del_pick")
    suspect_id = options[label]
    linked = db.child_counts("suspects", suspect_id)
    if linked:
        st.warning(
            "⚠️ This suspect is referenced by: "
            + ", ".join(f"**{t.replace('_', ' ')}** ({n})" for t, _, n in linked)
            + ". The confirmation dialog will offer to remove those records as well."
        )
    if st.button("🗑️ Delete this suspect record", key=f"suspect_del_btn_{suspect_id}", type="primary"):
        request_delete("suspects", suspect_id, label)


def render_suspects() -> None:
    """Suspect records page."""
    page_header(
        "🧾",
        "Suspect Records Management",
        "Photographic and biographical records of persons of interest to the command.",
    )
    if auth.is_viewer():
        readonly_notice()

    tabs = ["📋 Register & Photographs"]
    if auth.is_admin():
        tabs += ["➕ Add Suspect", "✏️ Edit Suspect", "🗑️ Delete Suspect"]
    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _suspect_view_tab()
    if auth.is_admin():
        with tab_objects[1]:
            _suspect_add_tab()
        with tab_objects[2]:
            _suspect_edit_tab()
        with tab_objects[3]:
            _suspect_delete_tab()


# --------------------------------------------------------------------------- #
#  PAGE: Search and retrieve
# --------------------------------------------------------------------------- #
def search_everything(term: str) -> dict[str, pd.DataFrame]:
    """
    Search the whole command database for ``term``.

    The search covers suspect names, case numbers, officer names and numbers,
    crime types, arrest locations and wanted-persons entries.
    """
    like = f"%{term}%"
    results: dict[str, pd.DataFrame] = {}

    suspect_rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT s.suspect_id, s.name AS "Name", s.sex AS "Sex", s.address AS "Address",
                   s.occupation AS "Occupation", s.age AS "Age", s.height AS "Height",
                   (SELECT COUNT(*) FROM cases c WHERE c.suspect_id = s.suspect_id) AS "Cases"
            FROM suspects s
            WHERE s.name LIKE ? OR s.address LIKE ? OR s.occupation LIKE ?
            ORDER BY s.name
            """,
            (like, like, like),
        )
    )
    if suspect_rows:
        frame = pd.DataFrame(suspect_rows)
        frame["Sex"] = frame["Sex"].map(lambda v: SEX_LABELS.get(v, v))
        results["Suspects"] = frame

    case_rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT c.case_id, c.case_number AS "Case Number", c.crime_type AS "Offence",
                   COALESCE(s.name, 'Not recorded') AS "Suspect",
                   COALESCE(o.name, 'Unassigned') AS "Officer",
                   c.status AS "Status", c.date_filed AS "Date Filed", c.description AS "Description"
            FROM cases c
            LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
            LEFT JOIN officers o ON o.officer_id = c.officer_id
            WHERE c.case_number LIKE ? OR c.crime_type LIKE ? OR c.description LIKE ?
               OR s.name LIKE ? OR o.name LIKE ? OR o.officer_number LIKE ?
            ORDER BY c.date_filed DESC
            """,
            (like, like, like, like, like, like),
        )
    )
    if case_rows:
        frame = pd.DataFrame(case_rows)
        frame["Date Filed"] = frame["Date Filed"].apply(fmt_date)
        results["Case Files"] = frame

    officer_rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT o.officer_id, o.officer_number AS "Officer No.", o.name AS "Name",
                   o.rank AS "Rank", o.department AS "Department", o.date_joined AS "Date Joined",
                   (SELECT COUNT(*) FROM cases c WHERE c.officer_id = o.officer_id) AS "Cases Handled"
            FROM officers o
            WHERE o.name LIKE ? OR o.officer_number LIKE ? OR o.rank LIKE ? OR o.department LIKE ?
            ORDER BY o.name
            """,
            (like, like, like, like),
        )
    )
    if officer_rows:
        frame = pd.DataFrame(officer_rows)
        frame["Date Joined"] = frame["Date Joined"].apply(fmt_date)
        results["Officers"] = frame

    arrest_rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT a.arrest_id, COALESCE(s.name, 'Not recorded') AS "Suspect",
                   COALESCE(o.name, 'Unassigned') AS "Officer",
                   COALESCE(c.case_number, 'Not linked') AS "Case Number",
                   a.arrest_date AS "Arrest Date", a.location AS "Location", a.notes AS "Notes"
            FROM arrests a
            LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
            LEFT JOIN officers o ON o.officer_id = a.officer_id
            LEFT JOIN cases c ON c.case_id = a.case_id
            WHERE s.name LIKE ? OR o.name LIKE ? OR o.officer_number LIKE ? OR c.case_number LIKE ?
               OR a.location LIKE ? OR a.notes LIKE ?
            ORDER BY a.arrest_date DESC
            """,
            (like, like, like, like, like, like),
        )
    )
    if arrest_rows:
        frame = pd.DataFrame(arrest_rows)
        frame["Arrest Date"] = frame["Arrest Date"].apply(fmt_date)
        results["Arrest Records"] = frame

    wanted_rows = db.rows_to_dicts(
        db.fetch_all(
            """
            SELECT w.wanted_id, COALESCE(s.name, 'Not recorded') AS "Suspect",
                   w.crime_type AS "Offence", w.reward_amount AS "Reward (NGN)",
                   w.last_seen AS "Last Seen", w.status AS "Status"
            FROM wanted_persons w
            LEFT JOIN suspects s ON s.suspect_id = w.suspect_id
            WHERE s.name LIKE ? OR w.crime_type LIKE ? OR w.last_seen LIKE ?
            ORDER BY w.date_added DESC
            """,
            (like, like, like),
        )
    )
    if wanted_rows:
        frame = pd.DataFrame(wanted_rows)
        frame["Reward (NGN)"] = frame["Reward (NGN)"].apply(naira)
        results["Wanted Persons"] = frame

    return results


def render_search() -> None:
    """Command-wide search and retrieval page."""
    page_header(
        "🔍",
        "Search and Retrieve",
        "Search the entire command database by suspect, case number, officer, "
        "offence or location.",
    )

    with st.form("global_search_form"):
        columns = st.columns([4, 1])
        term = columns[0].text_input(
            "Search term",
            value=st.session_state.get("search_term", ""),
            placeholder="e.g. Chinedu, OR/2026/001, 0785125, Armed Robbery, Ndeaboh...",
            label_visibility="collapsed",
        )
        submitted = columns[1].form_submit_button("🔍 Search", type="primary", **STRETCH)

    if submitted:
        st.session_state["search_term"] = term.strip()

    active_term = st.session_state.get("search_term", "")
    if not active_term:
        st.info(
            "💡 Enter a search term above. The search covers **suspect names**, "
            "**case numbers**, **officer names and force numbers**, **crime types**, "
            "**arrest locations** and **wanted persons**."
        )
        recent = cases_frame()
        if not recent.empty:
            st.markdown("#### 🕒 Most recent case files")
            st.dataframe(recent.head(5), hide_index=True, **STRETCH)
        return

    results = search_everything(active_term)
    total = sum(len(frame) for frame in results.values())

    if total == 0:
        st.warning(f"No record was found for **{active_term}**. Try a shorter search term.")
        return

    st.success(f"Found **{total}** matching record(s) for **{active_term}** across {len(results)} section(s).")

    for section in ("Suspects", "Case Files", "Officers", "Arrest Records", "Wanted Persons"):
        frame = results.get(section)
        if frame is None or frame.empty:
            continue
        with st.expander(f"📁 {section} — {len(frame)} match(es)", expanded=True):
            st.dataframe(frame.drop(columns=[c for c in frame.columns if c.endswith("_id")]),
                         hide_index=True, **STRETCH)
            download_csv(frame, f"search_{section.lower().replace(' ', '_')}.csv")

            # "Click on a result to view full details" - a select box plus a
            # detail panel, since Streamlit dataframes are not row-clickable.
            id_column = next((c for c in frame.columns if c.endswith("_id")), None)
            if id_column is None:
                continue
            options = {
                f"{row[frame.columns[1]]} | {row[frame.columns[2]]}": int(row[id_column])
                for row in frame.to_dict("records")
            }
            chosen = st.selectbox(
                f"View full details of a {section[:-1].lower()} record",
                list(options.keys()),
                key=f"search_pick_{section}",
            )
            record_id = options[chosen]
            _render_search_detail(section, record_id)


def _render_search_detail(section: str, record_id: int) -> None:
    """Show a full detail panel for a search result."""
    if section == "Suspects":
        row = db.fetch_one("SELECT * FROM suspects WHERE suspect_id = ?", (record_id,))
        if row is None:
            return
        left, right = st.columns([3, 1])
        with left:
            st.markdown(
                f"""
                <div class="npf-card">
                  <h4>{esc(row['name'])}</h4>
                  <div class="meta"><strong>Sex:</strong> {esc(SEX_LABELS.get(row['sex'], row['sex']))}
                      &nbsp;|&nbsp; <strong>Age:</strong> {esc(row['age'] or '-')}
                      &nbsp;|&nbsp; <strong>Height:</strong> {esc(row['height'] or '-')}</div>
                  <div class="meta"><strong>Address:</strong> {esc(row['address'] or '-')}</div>
                  <div class="meta"><strong>Occupation:</strong> {esc(row['occupation'] or '-')}</div>
                  <div class="meta"><strong>Date added:</strong> {esc(fmt_stamp(row['date_added']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            related = db.rows_to_dicts(
                db.fetch_all(
                    "SELECT case_number AS \"Case Number\", crime_type AS \"Offence\", "
                    "status AS \"Status\", date_filed AS \"Date Filed\" "
                    "FROM cases WHERE suspect_id = ? ORDER BY date_filed DESC",
                    (record_id,),
                )
            )
            if related:
                frame = pd.DataFrame(related)
                frame["Date Filed"] = frame["Date Filed"].apply(fmt_date)
                st.dataframe(frame, hide_index=True, **STRETCH)
            else:
                st.caption("No case file was opened against this suspect.")
        with right:
            photo = photo_data_uri(row["photo_path"])
            if photo:
                st.image(photo, width=200)
            else:
                st.info("No photograph on file.")
        return

    if section == "Case Files":
        row = db.fetch_one(
            """
            SELECT c.*, s.name AS suspect_name, o.name AS officer_name
            FROM cases c
            LEFT JOIN suspects s ON s.suspect_id = c.suspect_id
            LEFT JOIN officers o ON o.officer_id = c.officer_id
            WHERE c.case_id = ?
            """,
            (record_id,),
        )
        if row is None:
            return
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>{esc(row['case_number'])} — {esc(row['crime_type'])} {status_pill(row['status'])}</h4>
              <div class="meta"><strong>Suspect:</strong> {esc(row['suspect_name'] or 'Not recorded')}</div>
              <div class="meta"><strong>Investigating officer:</strong> {esc(row['officer_name'] or 'Unassigned')}</div>
              <div class="meta"><strong>Date filed:</strong> {esc(fmt_date(row['date_filed']))}</div>
              <div class="meta"><strong>Description:</strong> {esc(row['description'] or '-')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Open the *Intelligence Report* page to print this case.")
        return

    if section == "Officers":
        row = db.fetch_one("SELECT * FROM officers WHERE officer_id = ?", (record_id,))
        if row is None:
            return
        cases = db.rows_to_dicts(
            db.fetch_all(
                "SELECT case_number AS \"Case Number\", crime_type AS \"Offence\", "
                "status AS \"Status\" FROM cases WHERE officer_id = ? ORDER BY date_filed DESC",
                (record_id,),
            )
        )
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>{esc(officer_display(row['name'], row['rank'], row['officer_number']))}</h4>
              <div class="meta"><strong>Department:</strong> {esc(row['department'])}</div>
              <div class="meta"><strong>Date joined:</strong> {esc(fmt_date(row['date_joined']))}</div>
              <div class="meta"><strong>Case files assigned:</strong> {len(cases)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if cases:
            st.dataframe(pd.DataFrame(cases), hide_index=True, **STRETCH)
        return

    if section == "Arrest Records":
        row = db.fetch_one(
            """
            SELECT a.*, s.name AS suspect_name, c.case_number, o.name AS officer_name
            FROM arrests a
            LEFT JOIN suspects s ON s.suspect_id = a.suspect_id
            LEFT JOIN cases c ON c.case_id = a.case_id
            LEFT JOIN officers o ON o.officer_id = a.officer_id
            WHERE a.arrest_id = ?
            """,
            (record_id,),
        )
        if row is None:
            return
        st.markdown(
            f"""
            <div class="npf-card">
              <h4>Arrest of {esc(row['suspect_name'] or 'Not recorded')}</h4>
              <div class="meta"><strong>Date:</strong> {esc(fmt_date(row['arrest_date']))}
                  &nbsp;|&nbsp; <strong>Location:</strong> {esc(row['location'])}</div>
              <div class="meta"><strong>Case:</strong> {esc(row['case_number'] or 'Not linked')}
                  &nbsp;|&nbsp; <strong>Officer:</strong> {esc(row['officer_name'] or 'Not recorded')}</div>
              <div class="meta"><strong>Notes:</strong> {esc(row['notes'] or '-')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section == "Wanted Persons":
        row = db.fetch_one(
            """
            SELECT w.*, s.name AS suspect_name, s.photo_path, s.sex, s.age
            FROM wanted_persons w
            LEFT JOIN suspects s ON s.suspect_id = w.suspect_id
            WHERE w.wanted_id = ?
            """,
            (record_id,),
        )
        if row is None:
            return
        left, right = st.columns([3, 1])
        with left:
            st.markdown(
                f"""
                <div class="npf-card">
                  <h4>{esc(row['suspect_name'] or 'Not recorded')} {status_pill(row['status'])}</h4>
                  <div class="meta"><strong>Offence:</strong> {esc(row['crime_type'])}</div>
                  <div class="meta"><strong>Reward:</strong> {esc(naira(row['reward_amount']))}</div>
                  <div class="meta"><strong>Last seen:</strong> {esc(row['last_seen'] or '-')}</div>
                  <div class="meta"><strong>Entry added:</strong> {esc(fmt_stamp(row['date_added']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            photo = photo_data_uri(row["photo_path"])
            if photo:
                st.image(photo, width=200)
            else:
                st.info("No photograph on file.")


# --------------------------------------------------------------------------- #
#  PAGE: Intelligence report
# --------------------------------------------------------------------------- #
def render_report() -> None:
    """Computerized Intelligence Report generator."""
    page_header(
        "📄",
        "Intelligence Report Generator",
        "Produce the computerized intelligence report for any case file and download it.",
    )

    options = R.case_options()
    if not options:
        empty_state("There are no case files in the database yet.", "📄")
        return

    labels = {label: case_id for case_id, label in options}
    choice_col, meta_col = st.columns([2, 1])
    with choice_col:
        chosen = st.selectbox("Select the case file", list(labels.keys()), key="report_case_pick")
        case_id = labels[chosen]
    with meta_col:
        report_date = st.date_input("Date on report", value=dt.date.today(), key="report_date_pick")

    default_evidence = R.default_material_evidence(case_id)
    edit_col, sign_col = st.columns([3, 1])
    with edit_col:
        evidence = st.text_area(
            "Material evidence (editable)",
            value=default_evidence,
            height=100,
            key=f"report_evidence_{case_id}",
            help="Prefilled from the case description and any linked arrests. "
                 "Edit it before downloading if the exhibits differ.",
        )
    with sign_col:
        sign = st.text_input(
            "Signature / initials", value="", key=f"report_sign_{case_id}",
            placeholder="Leave blank to use the suspect's initials",
        )

    try:
        report = R.generate_intelligence_report(
            case_id,
            material_evidence=evidence,
            report_date=report_date,
            sign=sign.strip() or None,
            generated_by=auth.get_current_user().get("username", "system"),
        )
    except ValueError as error:
        st.error(str(error))
        return

    preview_col, side_col = st.columns([2.4, 1])

    with preview_col:
        st.markdown("#### 🖨️ Report preview")
        st.caption(
            "This is the exact layout that will be printed. Use the download buttons "
            "on the right (or Ctrl+P) to produce a hard copy."
        )
        st.markdown(R.format_report_as_html(report, standalone=False), unsafe_allow_html=True)

    with side_col:
        st.markdown("#### 📥 Download")
        try:
            pdf_bytes = R.format_report_as_pdf(report)
            st.download_button(
                "📕 Download as PDF",
                data=pdf_bytes,
                file_name=R.report_filename(report, "pdf"),
                mime="application/pdf",
                type="primary",
                **STRETCH,
            )
        except Exception as error:  # pragma: no cover - PDF writer guard
            st.error(f"The PDF could not be generated: {error}")

        st.download_button(
            "🌐 Download as HTML",
            data=R.format_report_as_html(report, standalone=True).encode("utf-8"),
            file_name=R.report_filename(report, "html"),
            mime="text/html",
            **STRETCH,
        )
        st.download_button(
            "📄 Download as TXT",
            data=R.format_report_as_text(report).encode("utf-8"),
            file_name=R.report_filename(report, "txt"),
            mime="text/plain",
            **STRETCH,
        )

        st.markdown("#### 🧾 Case summary")
        st.markdown(
            f"- **Case number:** {report['case_number']}\n"
            f"- **Offence:** {report['crime_type']}\n"
            f"- **Status:** {report['status']}\n"
            f"- **Date filed:** {report['date_filed_long']}\n"
            f"- **Suspect:** {report['suspect_name']}\n"
            f"- **Officer:** {report['officer_display']}\n"
            f"- **Department:** {report['department']}"
        )

        photo = photo_data_uri(report.get("photo_path"))
        st.markdown("#### 🖼️ Suspect photograph")
        if photo:
            st.image(photo, width=220)
        else:
            st.info("No photograph on file for this suspect.")

    if report["arrests"]:
        with st.expander(f"🚔 Arrests recorded on this case ({len(report['arrests'])})"):
            frame = pd.DataFrame(report["arrests"])
            frame["arrest_date"] = frame["arrest_date"].apply(fmt_date)
            frame = frame.rename(
                columns={
                    "arrest_id": "Arrest ID",
                    "arrest_date": "Arrest Date",
                    "location": "Location",
                    "notes": "Notes",
                    "officer_name": "Officer",
                    "officer_number": "Officer No.",
                }
            )
            st.dataframe(frame, hide_index=True, **STRETCH)

    with st.expander("📃 Plain text version (as it appears in the project document)"):
        st.code(R.format_report_as_text(report), language="text")


# --------------------------------------------------------------------------- #
#  PAGE: User management
# --------------------------------------------------------------------------- #
def render_users() -> None:
    """Administrator-only account management."""
    page_header(
        "👥",
        "User Management",
        "Create operator accounts and control who may view or amend command records.",
    )
    if not auth.require_admin():
        return

    users = auth.list_users()
    frame = pd.DataFrame(users)
    if not frame.empty:
        frame = frame.rename(
            columns={
                "user_id": "User ID",
                "username": "Username",
                "role": "Role",
                "created_at": "Created",
            }
        )
        frame["Created"] = frame["Created"].apply(fmt_stamp)
        st.dataframe(frame, hide_index=True, **STRETCH)
    st.caption(
        f"🔐 Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a random salt "
        f"({auth.PBKDF2_ITERATIONS:,} iterations). Plain text passwords are never saved."
    )

    tab_create, tab_password, tab_delete = st.tabs(
        ["➕ Create Account", "🔑 Reset Password", "🗑️ Delete Account"]
    )

    with tab_create:
        version = vkey("user_add")
        with st.form("user_add_form"):
            row1 = st.columns(2)
            username = row1[0].text_input("Username *", key=f"{version}_user")
            role = row1[1].selectbox("Role *", auth.ROLES, key=f"{version}_role")
            row2 = st.columns(2)
            password = row2[0].text_input("Password *", type="password", key=f"{version}_pwd")
            confirm = row2[1].text_input("Confirm Password *", type="password", key=f"{version}_pwd2")
            submitted = st.form_submit_button("💾 Create Account", type="primary", **STRETCH)

        if submitted:
            if password != confirm:
                st.error("The two passwords do not match.")
            else:
                try:
                    user_id = auth.create_user(username, password, role)
                except ValueError as error:
                    st.error(str(error))
                else:
                    bump("form_version_user_add")
                    flash("success", f"Account '{username.strip()}' created (user id {user_id}).")
                    st.rerun()

    with tab_password:
        if not users:
            empty_state("There are no accounts yet.")
        else:
            labels = {
                f"{u['username']} ({u['role']}) - id {u['user_id']}": int(u["user_id"]) for u in users
            }
            chosen = st.selectbox("Select the account", list(labels.keys()), key="user_pwd_pick")
            with st.form("user_password_form"):
                row1 = st.columns(2)
                new_password = row1[0].text_input("New password *", type="password", key="up_pwd")
                confirm_password = row1[1].text_input("Confirm password *", type="password", key="up_pwd2")
                submitted = st.form_submit_button("🔑 Update Password", type="primary", **STRETCH)
            if submitted:
                if new_password != confirm_password:
                    st.error("The two passwords do not match.")
                else:
                    try:
                        auth.change_password(labels[chosen], new_password)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        flash("success", "Password updated successfully.")
                        st.rerun()

    with tab_delete:
        if not users:
            empty_state("There are no accounts yet.")
        else:
            current = auth.get_current_user() or {}
            candidates = [u for u in users if int(u["user_id"]) != int(current.get("user_id", -1))]
            if not candidates:
                st.info("You cannot delete the account you are currently signed in with.")
            else:
                labels = {
                    f"{u['username']} ({u['role']}) - id {u['user_id']}": int(u["user_id"])
                    for u in candidates
                }
                chosen = st.selectbox("Select the account to delete", list(labels.keys()), key="user_del_pick")
                st.warning("The last remaining Administrator account cannot be deleted.")
                if st.button(
                    "🗑️ Delete this account",
                    key=f"user_del_btn_{labels[chosen]}",
                    type="primary",
                ):
                    request_delete("users", labels[chosen], chosen)


# --------------------------------------------------------------------------- #
#  Login page and database bootstrap
# --------------------------------------------------------------------------- #
def render_login() -> None:
    """Sign-in screen with role-aware branding."""
    left, middle, right = st.columns([1, 1.15, 1])
    with middle:
        st.markdown(
            """
            <div style="text-align:center; margin-top: 8px;">
              <div style="font-size:2.4rem;">🛡️</div>
              <h2 style="color:#0b2545; margin-bottom:0;">NIGERIA POLICE FORCE</h2>
              <p style="color:#5a6472; margin-top:4px;">
                Police Command Oji-River, Oji-River LGA, Enugu State<br/>
                <strong>Police Intelligence and Information Management System</strong>
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("### 🔐 Officer Sign In")
            st.caption("Enter your command credentials to continue.")

            with st.form("login_form"):
                username = st.text_input("Username", key="login_username", placeholder="e.g. admin")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("🔓 Sign In", type="primary", **STRETCH)

            attempts = int(st.session_state.get("failed_logins", 0))
            if attempts >= 5:
                st.error(
                    "🔒 Too many failed attempts in this session. "
                    "Close the browser tab and try again."
                )
            elif submitted:
                user = auth.login_user(username, password)
                if user is None:
                    st.session_state["failed_logins"] = attempts + 1
                    st.error("❌ Invalid username or password. Please try again.")
                else:
                    auth.session_login(user)
                    flash(
                        "success",
                        f"Welcome, {user['username']}. You are signed in as {user['role']}.",
                    )
                    st.rerun()

        with st.expander("ℹ️ Demonstration credentials"):
            st.markdown(
                """
                | Role | Username | Password | Privileges |
                |------|----------|----------|------------|
                | Administrator | `admin` | `admin123` | Add, edit, delete, view and generate reports |
                | Viewer | `viewer` | `viewer123` | View, search and generate reports only |
                """
            )
        st.caption(
            "Unauthorised access to police records is an offence under the Cybercrimes Act 2015. "
            "All sign-in attempts are the responsibility of the account holder."
        )


def render_setup_required() -> None:
    """Friendly bootstrap screen shown when the database has not been built."""
    page_header("🛠️", "System Setup Required", "The database has not been initialised on this computer.")
    st.warning(
        "The PIIMS database file was not found or is incomplete. "
        "Run **`python setup_db.py`** in the project folder, or press the button below."
    )
    st.code("python setup_db.py", language="bash")
    if st.button("🔧 Initialise the database now (creates tables and sample data)", type="primary"):
        try:
            db.init_db()
            setup_db.seed_all()
        except Exception as error:
            st.error(f"Initialisation failed: {error}")
        else:
            flash("success", "Database created and seeded with the Oji-River sample data.")
            st.rerun()


# --------------------------------------------------------------------------- #
#  Sidebar and router
# --------------------------------------------------------------------------- #
def render_sidebar() -> str:
    """Render the navigation sidebar and return the selected page key."""
    user = auth.get_current_user() or {}
    role = user.get("role", "Viewer")

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding-bottom:6px;">
              <div style="font-size:1.8rem;">🛡️</div>
              <div class="side-brand">NPF · PIIMS</div>
              <div class="side-sub">Oji-River Area Command</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="side-user">
              <div><strong>{esc(user.get('username', '-'))}</strong></div>
              <div class="role">{esc(role).upper()}</div>
              <div style="font-size:.72rem; color:#c8d4e3;">
                {esc('Full access' if role == 'Admin' else 'Read-only access')}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        available = [(key, label) for key, label, roles in NAV_ITEMS if role in roles]
        labels = dict(available)
        choice = st.radio(
            "Navigation",
            [key for key, _ in available],
            format_func=lambda key: labels[key],
            key="nav_page",
            label_visibility="collapsed",
        )
        st.session_state["page"] = choice

        st.markdown("---")
        stats = dashboard_stats()
        st.markdown("**📊 Live command figures**")
        st.caption(
            f"🗂️ {stats['active_cases']} active cases  \n"
            f"🚔 {stats['arrests']} arrests  \n"
            f"🎯 {stats['wanted_large']} at large  \n"
            f"👮 {stats['officers']} officers  \n"
            f"🧾 {stats['suspects']} suspects"
        )
        st.markdown("---")

        if st.button("🚪 Sign Out", key="logout_button", **STRETCH):
            auth.logout_user()
            st.rerun()

        st.caption(
            f"PIIMS v1.0  \n{dt.datetime.now().strftime('%d %B %Y, %H:%M')}  \n"
            "© Nigeria Police Force"
        )
    return st.session_state["page"]


PAGE_RENDERERS: dict[str, Callable[[], None]] = {
    "Dashboard": render_dashboard,
    "Case Files": render_cases,
    "Arrest Records": render_arrests,
    "Wanted Persons": render_wanted,
    "Officers": render_officers,
    "Suspects": render_suspects,
    "Search & Retrieve": render_search,
    "Intelligence Report": render_report,
    "User Management": render_users,
}


def main() -> None:
    """Application entry point."""
    inject_css()

    # ---- guard: database must exist ------------------------------------- #
    if not db.database_ready():
        render_setup_required()
        return

    # ---- guard: user must be signed in ---------------------------------- #
    if not auth.is_logged_in():
        render_login()
        return

    page = render_sidebar()
    show_flash()

    renderer = PAGE_RENDERERS.get(page, render_dashboard)
    try:
        renderer()
    except sqlite3.IntegrityError as error:
        st.error(
            "The database refused that operation because it would break a foreign-key "
            f"relationship: {error}"
        )
    except Exception as error:  # pragma: no cover - last-resort guard
        st.error(f"An unexpected error occurred while rendering this page: {error}")
        with st.expander("Technical details (for support)"):
            import traceback

            st.code(traceback.format_exc(), language="text")

    # Confirmation dialog for any pending deletion is rendered last so that it
    # appears on top of the page content.
    render_pending_delete()


if __name__ == "__main__":
    main()
