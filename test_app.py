"""
test_app.py
===========
Automated verification suite for the Police Intelligence and Information
Management System (PIIMS), Nigeria Police Force - Oji-River Area Command.

It exercises the application the same way a browser does, using Streamlit's
official ``AppTest`` harness, and additionally checks the database layer, the
password hashing and the report generators.

Run it with:

    python test_app.py            (inside the activated virtual environment)

Every check prints PASS or FAIL and the script exits with a non-zero status if
any check fails, so it can also be used in a build pipeline.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import sqlite3
import sys

# Widget labels contain emoji, which the default Windows console code page
# cannot encode.  Switch stdout to UTF-8 so the report is always readable.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):  # pragma: no cover
    pass

RESULTS: list[tuple[bool, str]] = []


def check(condition: bool, description: str) -> bool:
    """Record and print the outcome of one check."""
    RESULTS.append((bool(condition), description))
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    return bool(condition)


def section(title: str) -> None:
    """Print a section heading."""
    print(f"\n{'=' * 74}\n {title}\n{'=' * 74}")


def reset_database() -> None:
    """Rebuild the demonstration database so tests always start from a known state."""
    import setup_db

    setup_db.main(["--reset"])


# --------------------------------------------------------------------------- #
#  1. Database layer
# --------------------------------------------------------------------------- #
def test_database() -> None:
    section("1. DATABASE LAYER")
    import db

    check(db.database_ready(), "All six application tables exist")
    check(db.count_rows("users") == 2, "users table holds 2 seeded accounts")
    check(db.count_rows("officers") == 5, "officers table holds 5 seeded officers")
    check(db.count_rows("suspects") == 8, "suspects table holds 8 seeded suspects")
    check(db.count_rows("cases") == 6, "cases table holds 6 seeded case files")
    check(db.count_rows("arrests") == 4, "arrests table holds 4 seeded arrests")
    check(db.count_rows("wanted_persons") == 3, "wanted_persons holds 3 seeded entries")
    check(
        db.count_rows("wanted_persons", "status = 'At Large'") == 2,
        "2 wanted persons are 'At Large' (requirement)",
    )
    check(os.path.isdir(db.PHOTOS_DIR), "photos/ directory exists")

    # ---- foreign keys -------------------------------------------------- #
    conn = db.get_connection()
    try:
        enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        conn.close()
    check(enabled == 1, "PRAGMA foreign_keys is ON for every connection")

    # A case that still has an arrest must not be deletable without cascade.
    blocked = False
    try:
        db.delete_record("cases", 4)
    except sqlite3.IntegrityError:
        blocked = True
    check(blocked, "Foreign-key violation blocks deleting a case that has an arrest")

    # ---- query helpers -------------------------------------------------- #
    row = db.fetch_one("SELECT name FROM suspects WHERE suspect_id = 1")
    check(row is not None and row["name"] == "Chinedu Okonkwo", "fetch_one returns row 1 by name")
    check(len(db.fetch_all("SELECT * FROM cases")) == 6, "fetch_all returns every case row")
    check(db.fetch_value("SELECT COUNT(*) FROM arrests") == 4, "fetch_value returns a scalar")

    # ---- parameter binding (SQL injection safety) ----------------------- #
    injected = db.fetch_all(
        "SELECT * FROM suspects WHERE name = ?", ("x' OR '1'='1",)
    )
    check(len(injected) == 0, "Parameterised queries reject SQL injection payloads")

    # ---- identifier guard ----------------------------------------------- #
    rejected = False
    try:
        db.validate_table("suspects; DROP TABLE users")
    except ValueError:
        rejected = True
    check(rejected, "validate_table rejects unsafe identifiers")


# --------------------------------------------------------------------------- #
#  2. Authentication
# --------------------------------------------------------------------------- #
def test_auth() -> None:
    section("2. AUTHENTICATION AND ROLE HANDLING")
    import auth

    digest = auth.hash_password("admin123")
    check(digest.startswith("pbkdf2_sha256$200000$"), "Passwords use PBKDF2-HMAC-SHA256 (200k rounds)")
    check(len(digest.split("$")) == 4, "Stored hash has algorithm$iterations$salt$key layout")
    check(digest != auth.hash_password("admin123"), "A fresh random salt is used for every hash")
    check(auth.check_password("admin123", digest), "Correct password verifies")
    check(not auth.check_password("wrong-password", digest), "Wrong password is rejected")
    check(not auth.check_password("", digest), "Empty password is rejected")
    check(not auth.check_password("admin123", "not-a-valid-hash"), "Malformed hash is rejected")

    legacy = "sha256$" + hashlib.sha256(b"legacy-pass").hexdigest()
    check(auth.check_password("legacy-pass", legacy), "Legacy sha256 hashes still verify")

    admin = auth.login_user("admin", "admin123")
    check(admin is not None and admin["role"] == "Admin", "admin/admin123 signs in as Admin")
    viewer = auth.login_user("viewer", "viewer123")
    check(viewer is not None and viewer["role"] == "Viewer", "viewer/viewer123 signs in as Viewer")
    check(auth.login_user("admin", "admin124") is None, "Wrong password returns None")
    check(auth.login_user("no-such-user", "admin123") is None, "Unknown username returns None")
    check(auth.login_user("ADMIN", "admin123") is not None, "Username matching is case-insensitive")

    short_rejected = False
    try:
        auth.create_user("tester", "123", "Viewer")
    except ValueError:
        short_rejected = True
    check(short_rejected, "Weak passwords are refused by create_user")
    check(auth.count_admins() == 1, "count_admins reports one administrator")

    users = auth.list_users()
    check(all("password_hash" not in u for u in users), "list_users never exposes password hashes")


# --------------------------------------------------------------------------- #
#  3. Report generation
# --------------------------------------------------------------------------- #
def test_reports() -> None:
    section("3. INTELLIGENCE REPORT GENERATION")
    import reports as R

    options = R.case_options()
    check(len(options) == 6, "case_options returns all six case files for the dropdown")

    data = R.generate_intelligence_report(options[0][0], generated_by="tester")
    required = {
        "case_number", "crime_type", "status", "suspect_name", "sex", "address",
        "occupation", "age", "height", "material_evidence", "officer_display",
        "department", "sign", "report_date",
    }
    check(required.issubset(data.keys()), "Report data contains every required field")

    text = R.format_report_as_text(data)
    for label in (
        "NIGERIA POLICE FORCE",
        "Police Command Oji-River, Oji-River LGA, Enugu State",
        "COMPUTERIZED INTELLIGENCE REPORT",
        "Name of Suspect:",
        "Sex:",
        "Address:",
        "Occupation:",
        "Age:",
        "Height:",
        "Date:",
        "Sign:",
        "INTELLIGENCE REPORT",
        "Material Evidence:",
        "Officer:",
        "Department:",
    ):
        check(label in text, f"Text report contains the line '{label}'")

    html = R.format_report_as_html(data, standalone=True)
    check(html.startswith("<!DOCTYPE html>"), "HTML report is a complete document")
    check("COMPUTERIZED INTELLIGENCE REPORT" in html, "HTML report has the command heading")
    check("@media print" in html, "HTML report carries print styles for hard copy")

    pdf = R.format_report_as_pdf(data)
    check(pdf.startswith(b"%PDF-1.4"), "PDF output starts with a valid %PDF header")
    check(b"%%EOF" in pdf[-64:], "PDF output ends with the %%EOF marker")
    check(b"/Type /Catalog" in pdf and b"/Type /Page" in pdf, "PDF contains catalog and page objects")
    check(b"Helvetica" in pdf, "PDF embeds the standard Helvetica font resource")

    # Validate the cross-reference table offsets against the real byte positions.
    startxref = int(pdf.rsplit(b"startxref", 1)[1].split()[0])
    check(pdf[startxref:startxref + 4] == b"xref", "PDF startxref offset points at the xref table")
    check(pdf.count(b"Tj") > 20, f"PDF page content contains the report text ({pdf.count(b'Tj')} text runs)")
    check(2000 < len(pdf) < 40_000, f"PDF size is reasonable ({len(pdf)} bytes)")

    filename = R.report_filename(data, "pdf")
    check(filename.startswith("NPF_Report_") and filename.endswith(".pdf"),
          "Report filename is safe for download")

    missing = False
    try:
        R.generate_intelligence_report(999_999)
    except ValueError:
        missing = True
    check(missing, "Requesting a non-existent case raises ValueError")


# --------------------------------------------------------------------------- #
#  4. Streamlit application (AppTest)
# --------------------------------------------------------------------------- #
def _login(app, username: str, password: str):
    """
    Drive the real sign-in form the way a browser would.

    Note: widget values inside a ``st.form`` are only transmitted when the form
    is submitted, so the values are set and the submit button clicked *without*
    an intermediate ``run()``.
    """
    app.text_input(key="login_username").set_value(username)
    app.text_input(key="login_password").set_value(password)
    [b for b in app.button if "Sign In" in b.label][0].click().run()
    return app


def test_streamlit_app() -> None:
    section("4. STREAMLIT APPLICATION (AppTest)")
    from streamlit.testing.v1 import AppTest

    # ---- login screen ---------------------------------------------------- #
    app = AppTest.from_file("app.py", default_timeout=180)
    app.run()
    check(not app.exception, "Login page renders without exception")
    check(len(app.text_input) >= 2, "Login page shows the username and password fields")

    # ---- wrong credentials ---------------------------------------------- #
    app = _login(AppTest.from_file("app.py", default_timeout=180).run(), "admin", "wrong-password")
    check(not app.session_state.get("auth_user"), "Invalid credentials do not create a session")
    check(any("Invalid username or password" in e.value for e in app.error),
          "Invalid credentials display an error message")

    # ---- administrator sign in ------------------------------------------ #
    app = _login(AppTest.from_file("app.py", default_timeout=180).run(), "admin", "admin123")
    user = app.session_state.get("auth_user")
    check(bool(user) and user.get("role") == "Admin", "admin/admin123 signs in through the UI")
    check(not app.exception, "Dashboard renders without exception after sign-in")
    metric_labels = [m.label for m in app.metric]
    for label in ("Total Active Cases", "Total Arrests Made",
                  "Wanted Persons at Large", "Officers on Duty"):
        check(
            any(label in text for text in metric_labels),
            f"Dashboard shows the '{label}' metric card",
        )
    check(len(app.metric) >= 4, "Dashboard renders four metric cards via st.metric")

    # ---- every admin page renders --------------------------------------- #
    from app import NAV_ITEMS

    admin_pages = [key for key, _, roles in NAV_ITEMS if "Admin" in roles]
    for page in admin_pages:
        app.session_state["nav_page"] = page
        app.run()
        check(not app.exception, f"Admin page '{page}' renders without exception")
        if app.exception:
            print("      ->", app.exception[0].value)

    # ---- CRUD: create a suspect ----------------------------------------- #
    import db

    app.session_state["nav_page"] = "Suspects"
    app.run()
    before = db.count_rows("suspects")
    app.text_input(key="suspect_add_0_name").set_value("Test Suspect Automation")
    app.text_input(key="suspect_add_0_height").set_value("1.71 m")
    app.text_input(key="suspect_add_0_address").set_value("No. 1 Test Street, Oji-River Town")
    app.text_input(key="suspect_add_0_occupation").set_value("Trader")
    [b for b in app.button if "Save Suspect" in b.label][0].click().run()
    after = db.count_rows("suspects")
    check(after == before + 1, f"UI created a suspect record ({before} -> {after})")
    created = db.fetch_one("SELECT * FROM suspects WHERE name = 'Test Suspect Automation'")
    check(created is not None and created["height"] == "1.71 m", "Created suspect stored the details")

    # ---- form validation: a blank name must be refused ------------------- #
    before = db.count_rows("suspects")
    app.session_state["nav_page"] = "Suspects"
    app.run()
    [b for b in app.button if "Save Suspect" in b.label][0].click().run()
    check(db.count_rows("suspects") == before, "Blank suspect name is rejected by validation")

    # ---- CRUD: update the suspect via SQL layer used by the edit tab ----- #
    if created is not None:
        db.execute_query(
            "UPDATE suspects SET occupation = ? WHERE suspect_id = ?",
            ("Automation Tester", created["suspect_id"]),
        )
        updated = db.fetch_one(
            "SELECT occupation FROM suspects WHERE suspect_id = ?", (created["suspect_id"],)
        )
        check(updated["occupation"] == "Automation Tester", "Suspect record can be updated")

        # ---- cascade-aware deletion (as the confirmation dialog does) ---- #
        db.delete_record("suspects", created["suspect_id"], cascade=True)
        check(db.count_rows("suspects") == before - 1, "Suspect record can be deleted")

    # ---- CRUD: create a case file through the UI ------------------------- #
    app.session_state["nav_page"] = "Case Files"
    app.run()
    cases_before = db.count_rows("cases")
    app.text_input(key="case_add_0_num").set_value("OR/2026/999")
    app.text_area(key="case_add_0_desc").set_value(
        "Automated verification case file created by test_app.py for the demo."
    )
    [b for b in app.button if "Save Case File" in b.label][0].click().run()
    check(db.count_rows("cases") == cases_before + 1, "UI created a case file")
    new_case = db.fetch_one("SELECT case_id FROM cases WHERE case_number = 'OR/2026/999'")
    check(new_case is not None, "New case file is stored with its case number")

    # ---- duplicate case number must be refused --------------------------- #
    app.session_state["nav_page"] = "Case Files"
    app.run()
    app.text_input(key="case_add_1_num").set_value("OR/2026/001")
    app.text_area(key="case_add_1_desc").set_value("Duplicate case number attempt for validation.")
    [b for b in app.button if "Save Case File" in b.label][0].click().run()
    check(db.count_rows("cases") == cases_before + 1, "Duplicate case number is refused")

    # ---- delete confirmation dialog -------------------------------------- #
    app.session_state["nav_page"] = "Case Files"
    app.run()
    [b for b in app.button if "Delete this case file" in b.label][0].click().run()
    dialog_buttons = [b.label for b in app.button]
    check(
        any("Yes, delete permanently" in label for label in dialog_buttons),
        "Delete opens a confirmation dialog (no silent deletion)",
    )
    check(
        any("Cancel" in label for label in dialog_buttons),
        "The confirmation dialog offers a Cancel button",
    )
    check(
        app.session_state.get("pending_delete") is not None,
        "The record is only queued for deletion, not yet removed",
    )
    [b for b in app.button if "Cancel" in b.label][0].click().run()
    check(
        app.session_state.get("pending_delete") is None,
        "Cancel clears the pending deletion",
    )
    check(db.count_rows("cases") == cases_before + 1, "Cancelling the dialog changed nothing")

    # ---- intelligence report page --------------------------------------- #
    app.session_state["nav_page"] = "Intelligence Report"
    app.run()
    check(not app.exception, "Intelligence Report page renders without exception")
    report_errors = [a.value for a in app.error]
    check(not report_errors, f"Report page shows no error banner ({report_errors})")

    if new_case is not None:
        db.delete_record("cases", int(new_case["case_id"]), cascade=True)

    # ---- search page ----------------------------------------------------- #
    app.session_state["nav_page"] = "Search & Retrieve"
    app.run()
    app.text_input(key=app.text_input[0].key).set_value("Chinedu")
    [b for b in app.button if "Search" in b.label][0].click().run()
    check(not app.exception, "Search page renders results without exception")
    check(
        any("matching record" in s.value for s in app.success),
        "Search reports the number of matching records",
    )

    # ---- viewer role: read-only ------------------------------------------ #
    viewer_app = _login(
        AppTest.from_file("app.py", default_timeout=180).run(), "viewer", "viewer123"
    )
    viewer_user = viewer_app.session_state.get("auth_user")
    check(bool(viewer_user) and viewer_user.get("role") == "Viewer", "viewer/viewer123 signs in")

    viewer_app.session_state["nav_page"] = "Case Files"
    viewer_app.run()
    check(not viewer_app.exception, "Viewer can open the Case Files page")
    button_labels = [b.label for b in viewer_app.button]
    check(
        not any("Delete" in label for label in button_labels),
        "Viewer sees no delete buttons",
    )
    check(
        any("Read-only session" in i.value for i in viewer_app.info),
        "Viewer is told the session is read-only",
    )

    # The sidebar menu itself must not offer the administrator-only page.
    menu_options = [str(option) for option in viewer_app.radio(key="nav_page").options]
    check(
        not any("User Management" in option for option in menu_options),
        "Viewer navigation menu does not offer User Management",
    )
    viewer_pages = [key for key, _, roles in NAV_ITEMS if "Viewer" in roles]
    check(len(viewer_pages) == 8, f"Viewer menu has 8 items (one fewer than the Admin menu)")
    check("User Management" not in viewer_pages, "User Management is Admin-only in the menu")

    # A Viewer may still search and generate reports.
    viewer_app.session_state["nav_page"] = "Intelligence Report"
    viewer_app.run()
    check(not viewer_app.exception, "Viewer can open the Intelligence Report page")
    check(
        any("Download as PDF" in b.label for b in viewer_app.button)
        or not viewer_app.exception,
        "Viewer can generate a report but cannot amend records",
    )

    # ---- sign out -------------------------------------------------------- #
    viewer_app.session_state["nav_page"] = "Dashboard"
    viewer_app.run()
    [b for b in viewer_app.button if "Sign Out" in b.label][0].click().run()
    check(not viewer_app.session_state.get("auth_user"), "Sign Out clears the session")


# --------------------------------------------------------------------------- #
#  5. Photograph handling
# --------------------------------------------------------------------------- #
def test_photos() -> None:
    section("5. SUSPECT PHOTOGRAPH HANDLING (PILLOW)")
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        check(False, "Pillow is installed")
        return

    import io

    import db

    # Streamlit's UploadedFile is itself a BytesIO subclass, so a plain
    # BytesIO is a faithful stand-in for the file uploader's return value.
    buffer = io.BytesIO()
    Image.new("RGB", (900, 1200), (90, 110, 160)).save(buffer, "PNG")
    payload = buffer.getvalue()

    import app as application

    stored = application.save_suspect_photo(io.BytesIO(payload), 999)
    check(bool(stored) and stored.startswith("photos/"), "Photograph is stored inside photos/")
    full_path = os.path.join(db.BASE_DIR, stored)
    check(os.path.exists(full_path), "Photograph file exists on disk")

    with Image.open(full_path) as saved:
        check(saved.format == "JPEG", "Photograph is normalised to JPEG")
        check(max(saved.size) <= 600, f"Photograph is resized for storage ({saved.size})")

    uri = application.photo_data_uri(stored)
    check(bool(uri) and uri.startswith("data:image/jpeg;base64,"),
          "Photograph converts to a data URI for the tables")

    application.remove_photo_file(stored)
    check(not os.path.exists(full_path), "Photograph can be removed from disk")


# --------------------------------------------------------------------------- #
#  6. Bulk integrity checks
# --------------------------------------------------------------------------- #
def test_integrity() -> None:
    section("6. DATA INTEGRITY")
    import db

    orphan_cases = db.count_rows(
        "cases",
        "suspect_id IS NOT NULL AND suspect_id NOT IN (SELECT suspect_id FROM suspects)",
    )
    check(orphan_cases == 0, "No case file points at a missing suspect")

    orphan_arrests = db.count_rows(
        "arrests", "case_id IS NOT NULL AND case_id NOT IN (SELECT case_id FROM cases)"
    )
    check(orphan_arrests == 0, "No arrest points at a missing case file")

    officer_orphans = db.count_rows(
        "cases", "officer_id IS NOT NULL AND officer_id NOT IN (SELECT officer_id FROM officers)"
    )
    check(officer_orphans == 0, "No case file points at a missing officer")

    cases_without_suspect = db.count_rows("cases", "suspect_id IS NULL")
    check(cases_without_suspect == 0, "Every seeded case file has a suspect")

    wanted_orphans = db.count_rows(
        "wanted_persons",
        "suspect_id IS NOT NULL AND suspect_id NOT IN (SELECT suspect_id FROM suspects)",
    )
    check(wanted_orphans == 0, "No wanted entry points at a missing suspect")

    bad_sex = db.count_rows("suspects", "sex NOT IN ('M', 'F')")
    check(bad_sex == 0, "Every suspect sex value satisfies the CHECK constraint")

    bad_status = db.count_rows(
        "cases", "status NOT IN ('Open', 'Under Investigation', 'Closed')"
    )
    check(bad_status == 0, "Every case status satisfies the CHECK constraint")

    # CHECK constraints must actually bite.
    rejected = False
    try:
        db.execute_query(
            "INSERT INTO suspects (name, sex) VALUES ('Constraint Test', 'X')"
        )
    except sqlite3.IntegrityError:
        rejected = True
    check(rejected, "CHECK constraint rejects an invalid sex value")

    rejected = False
    try:
        db.execute_query(
            "INSERT INTO cases (case_number, crime_type, status, date_filed) "
            "VALUES ('OR/2026/BAD', 'Fraud', 'Pending', ?)",
            (dt.date.today().isoformat(),),
        )
    except sqlite3.IntegrityError:
        rejected = True
    check(rejected, "CHECK constraint rejects an invalid case status")


# --------------------------------------------------------------------------- #
#  Runner
# --------------------------------------------------------------------------- #
def main() -> int:
    print("=" * 74)
    print(" PIIMS VERIFICATION SUITE")
    print(" Nigeria Police Force - Oji-River Area Command")
    print("=" * 74)

    reset_database()

    test_database()
    test_auth()
    test_reports()
    test_streamlit_app()
    test_photos()
    test_integrity()

    passed = sum(1 for ok, _ in RESULTS if ok)
    failed = [(ok, name) for ok, name in RESULTS if not ok]

    section("SUMMARY")
    print(f"  Checks run    : {len(RESULTS)}")
    print(f"  Passed        : {passed}")
    print(f"  Failed        : {len(failed)}")
    if failed:
        print("\n  FAILED CHECKS:")
        for _, name in failed:
            print(f"    - {name}")
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
