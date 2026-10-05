"""
setup_db.py
===========
One-shot database builder for the
POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS)
Nigeria Police Force - Oji-River Area Command, Enugu State.

What it does
------------
1. Creates the ``photos/`` directory if it does not exist.
2. Creates every table, index and foreign-key relationship (see ``db.SCHEMA_SQL``).
3. Seeds realistic demonstration data for the Oji-River Area Command:
       * 2 user accounts        (1 Admin + 1 Viewer)
       * 5 officers             (Intelligence, Crime Investigation, Fraud Investigation)
       * 8 suspects             (varied ages, sexes, occupations, addresses)
       * 6 case files           (Open / Under Investigation / Closed)
       * 4 arrest records       (each linked to a case, a suspect and an officer)
       * 3 wanted persons       (2 At Large, 1 Captured)

Usage
-----
    python setup_db.py              # create tables + seed if the database is empty
    python setup_db.py --reset      # drop everything, rebuild and reseed
    python setup_db.py --status     # show a row count for every table

The script is safe to run more than once: seeding is skipped when the database
already holds records, so a demonstration database is never overwritten unless
``--reset`` is passed explicitly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Iterable, Sequence

import db
from auth import hash_password

# --------------------------------------------------------------------------- #
#  Default accounts
# --------------------------------------------------------------------------- #
DEFAULT_USERS: list[tuple[int, str, str, str]] = [
    # (user_id, username, plain_password, role)
    (1, "admin", "admin123", "Admin"),
    (2, "viewer", "viewer123", "Viewer"),
]

# --------------------------------------------------------------------------- #
#  Officers - Nigeria Police Force, Oji-River Area Command
# --------------------------------------------------------------------------- #
OFFICERS: list[tuple[int, str, str, str, str, int]] = [
    # (officer_id, officer_number, name, rank, department, days_ago_joined)
    (1, "0785124", "Musa Ibrahim", "Deputy Superintendent of Police", "Intelligence", 4200),
    (2, "0785125", "Ngozi Okafor", "Assistant Superintendent of Police", "Crime Investigation", 3100),
    (3, "0785126", "Chukwudi Eze", "Inspector", "Fraud Investigation", 4800),
    (4, "0785127", "Amina Bello", "Sergeant", "Intelligence", 2500),
    (5, "0785128", "Emeka Nwosu", "Inspector", "Crime Investigation", 4400),
]

# --------------------------------------------------------------------------- #
#  Suspects
# --------------------------------------------------------------------------- #
SUSPECTS: list[tuple[int, str, str, str, str, int, str, int]] = [
    # (suspect_id, name, sex, address, occupation, age, height, days_ago_added)
    (1, "Chinedu Okonkwo", "M", "No. 12 Ugwu Street, Oji-River Town", "Trader", 34, "1.72 m", 130),
    (2, "Blessing Nwankwo", "F", "No. 5 Aba Road, Ndeaboh", "Tailor", 29, "1.63 m", 100),
    (3, "Emeka Obi", "M", "Umueze Village, Agbani", "Farmer", 41, "1.80 m", 80),
    (4, "Fatima Sani", "F", "No. 8 Zik Avenue, Udi", "Student", 26, "1.58 m", 65),
    (5, "Ikechukwu Madu", "M", "No. 23 Ogui Road, Akegbe Ugwu", "Mechanic", 38, "1.75 m", 155),
    (6, "Ngozi Ude", "F", "No. 3 Market Road, Oji-River Town", "Businesswoman", 45, "1.66 m", 30),
    (7, "Yakubu Danladi", "M", "No. 17 Station Road, Ndeaboh", "Driver", 31, "1.69 m", 45),
    (8, "Chioma Eze", "F", "No. 9 College Road, Agbani", "Teacher", 33, "1.61 m", 55),
]

# --------------------------------------------------------------------------- #
#  Case files - case numbers follow the OR/<year>/<serial> convention
# --------------------------------------------------------------------------- #
CASES: list[tuple[int, int, int, int, str, str, str, int]] = [
    # (case_id, case_number, suspect_id, officer_id, crime_type, description, status, days_ago_filed)
    (
        1, "OR/{year}/001", 1, 2, "Armed Robbery",
        "Armed robbery at a provision store along the old Enugu-Onitsha road, Oji-River Town. "
        "Two suspects armed with a locally made pistol carted away cash and goods valued at "
        "NGN 450,000 before fleeing on a motorcycle.",
        "Open", 118,
    ),
    (
        2, "OR/{year}/002", 2, 3, "Fraud",
        "Obtained the sum of NGN 1,250,000 from a cooperative society in Ndeaboh under the "
        "pretext of supplying 200 bags of rice which were never delivered.",
        "Under Investigation", 96,
    ),
    (
        3, "OR/{year}/003", 3, 5, "Kidnapping",
        "Abduction of a businessman at Akegbe Ugwu junction. A ransom of NGN 2,000,000 was "
        "demanded and the victim was released after three days in captivity.",
        "Under Investigation", 74,
    ),
    (
        4, "OR/{year}/004", 5, 2, "Theft",
        "Theft of motorcycle spare parts from a mechanic workshop at Udi. The suspect made a "
        "voluntary confession and the items were recovered intact.",
        "Closed", 150,
    ),
    (
        5, "OR/{year}/005", 7, 4, "Assault",
        "Assault occasioning grievous harm on a commercial motorcyclist at Ndeaboh motor park "
        "following a disagreement over transport fare. The victim was treated at the "
        "General Hospital, Oji-River.",
        "Open", 41,
    ),
    (
        6, "OR/{year}/006", 6, 3, "Fraud",
        "Fraudulent collection of NGN 680,000 from market women in Oji-River Town as "
        "contribution towards a non-existent empowerment scheme.",
        "Under Investigation", 25,
    ),
]

# --------------------------------------------------------------------------- #
#  Arrest records
# --------------------------------------------------------------------------- #
ARRESTS: list[tuple[int, int, int, int, int, str, str]] = [
    # (arrest_id, suspect_id, officer_id, case_id, days_ago, location, notes)
    (
        1, 5, 2, 4, 145, "Udi",
        "Suspect arrested at his residence; all the stolen motorcycle spare parts were recovered.",
    ),
    (
        2, 1, 2, 1, 110, "Oji-River Town",
        "Arrested at a drinking joint along Aba Road; one locally made pistol and NGN 85,000 recovered.",
    ),
    (
        3, 3, 5, 3, 60, "Agbani",
        "Arrested at the point of collecting ransom; the sum of NGN 500,000 was recovered from him.",
    ),
    (
        4, 2, 3, 2, 40, "Ndeaboh",
        "Arrested at Ndeaboh main market. She has volunteered a statement and is assisting the investigation.",
    ),
]

# --------------------------------------------------------------------------- #
#  Wanted persons
# --------------------------------------------------------------------------- #
WANTED: list[tuple[int, int, str, float, str, str, int]] = [
    # (wanted_id, suspect_id, crime_type, reward_amount, last_seen, status, days_ago_added)
    (1, 4, "Fraud", 250_000.0, "Udi main market, Udi LGA, Enugu State", "At Large", 62),
    (2, 8, "Kidnapping", 500_000.0, "College Road, Agbani, Nsukka LGA", "At Large", 50),
    (3, 2, "Fraud", 150_000.0, "Ndeaboh main market, Aninri LGA", "Captured", 90),
]


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def days_ago(days: int) -> str:
    """Return an ISO date string ``days`` days before today."""
    return (dt.date.today() - dt.timedelta(days=days)).isoformat()


def timestamp_days_ago(days: int) -> str:
    """Return a ``YYYY-MM-DD HH:MM:SS`` timestamp ``days`` days before now."""
    moment = dt.datetime.now() - dt.timedelta(days=days)
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _insert_many(statement: str, rows: Iterable[Sequence[object]]) -> int:
    """Insert rows one at a time, reporting any that SQLite refuses."""
    inserted = 0
    for row in rows:
        try:
            db.execute_query(statement, tuple(row))
            inserted += 1
        except Exception as exc:  # pragma: no cover - defensive
            print(f"   ! skipped row {row[:2]}: {exc}")
    return inserted


# --------------------------------------------------------------------------- #
#  Seeding
# --------------------------------------------------------------------------- #
def seed_users() -> int:
    """Create the default Admin and Viewer accounts."""
    rows = [
        (user_id, username, hash_password(password), role)
        for user_id, username, password, role in DEFAULT_USERS
    ]
    return _insert_many(
        "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
        rows,
    )


def seed_officers() -> int:
    """Create the five officers of the Area Command."""
    rows = [
        (oid, number, name, rank, dept, days_ago(joined))
        for oid, number, name, rank, dept, joined in OFFICERS
    ]
    return _insert_many(
        "INSERT INTO officers (officer_id, officer_number, name, rank, department, date_joined) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_suspects() -> int:
    """Create the eight suspect records (no photographs at this stage)."""
    rows = [
        (sid, name, sex, address, occupation, age, height, None, timestamp_days_ago(added))
        for sid, name, sex, address, occupation, age, height, added in SUSPECTS
    ]
    return _insert_many(
        "INSERT INTO suspects "
        "(suspect_id, name, sex, address, occupation, age, height, photo_path, date_added) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_cases() -> int:
    """Create the six case files using the current year in the case number."""
    year = dt.date.today().year
    rows = [
        (cid, number.format(year=year), suspect_id, officer_id, crime, description, status,
         days_ago(filed))
        for cid, number, suspect_id, officer_id, crime, description, status, filed in CASES
    ]
    return _insert_many(
        "INSERT INTO cases "
        "(case_id, case_number, suspect_id, officer_id, crime_type, description, status, date_filed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_arrests() -> int:
    """Create the four arrest records, each linked to a case, suspect and officer."""
    rows = [
        (aid, suspect_id, officer_id, case_id, days_ago(ago), location, notes)
        for aid, suspect_id, officer_id, case_id, ago, location, notes in ARRESTS
    ]
    return _insert_many(
        "INSERT INTO arrests "
        "(arrest_id, suspect_id, officer_id, case_id, arrest_date, location, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_wanted() -> int:
    """Create the three wanted-person entries."""
    rows = [
        (wid, suspect_id, crime, reward, last_seen, status, timestamp_days_ago(added))
        for wid, suspect_id, crime, reward, last_seen, status, added in WANTED
    ]
    return _insert_many(
        "INSERT INTO wanted_persons "
        "(wanted_id, suspect_id, crime_type, reward_amount, last_seen, status, date_added) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_all() -> dict[str, int]:
    """Seed every table and return the number of rows created per table."""
    return {
        "users": seed_users(),
        "officers": seed_officers(),
        "suspects": seed_suspects(),
        "cases": seed_cases(),
        "arrests": seed_arrests(),
        "wanted_persons": seed_wanted(),
    }


# --------------------------------------------------------------------------- #
#  Reporting
# --------------------------------------------------------------------------- #
def print_status() -> None:
    """Print a small table with the row count of every table."""
    print("\n  TABLE                 ROWS")
    print("  " + "-" * 30)
    for table in db.ALLOWED_TABLES:
        if db.table_exists(table):
            print(f"  {table:<20} {db.count_rows(table):>5}")
        else:
            print(f"  {table:<20} {'MISSING':>5}")
    print()


def print_summary() -> None:
    """Print the command statistics that the dashboard will display."""
    active = db.count_rows("cases", "status IN ('Open', 'Under Investigation')")
    at_large = db.count_rows("wanted_persons", "status = 'At Large'")
    print("  COMMAND SUMMARY")
    print("  " + "-" * 30)
    print(f"  Total case files          : {db.count_rows('cases')}")
    print(f"  Active cases              : {active}")
    print(f"  Arrests recorded          : {db.count_rows('arrests')}")
    print(f"  Wanted persons at large   : {at_large}")
    print(f"  Officers in the command   : {db.count_rows('officers')}")
    print(f"  Suspects on record        : {db.count_rows('suspects')}")
    print()


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and seed the PIIMS database (Nigeria Police Force, Oji-River Area Command)."
    )
    parser.add_argument("--reset", action="store_true",
                        help="Drop all tables, recreate them and reseed the sample data.")
    parser.add_argument("--status", action="store_true",
                        help="Only display the current row counts.")
    parser.add_argument("--force", action="store_true",
                        help="Seed even when the database already contains records.")
    args = parser.parse_args(argv)

    print("=" * 68)
    print(" NIGERIA POLICE FORCE - Oji-River Area Command")
    print(" Police Intelligence and Information Management System (PIIMS)")
    print(" Database setup")
    print("=" * 68)
    print(f"\n  Database file : {db.DB_PATH}")
    print(f"  Photos folder : {db.ensure_photos_dir()}")

    if args.status:
        print_status()
        print_summary()
        return 0

    if args.reset:
        print("\n  [1/3] Resetting the database ...")
        db.reset_db()
    else:
        print("\n  [1/3] Creating tables if they do not exist ...")
        db.init_db()
    print("        Tables ready (foreign keys enforced).")

    # Seed only when the database is empty, unless the operator forces it.
    already_seeded = db.table_exists("users") and db.count_rows("users") > 0
    if already_seeded and not (args.reset or args.force):
        print("\n  [2/3] Sample data already present - seeding skipped.")
        print("        (run 'python setup_db.py --reset' to rebuild from scratch)")
    else:
        print("\n  [2/3] Inserting sample Oji-River command data ...")
        counts = seed_all()
        for table, n in counts.items():
            print(f"        {table:<16} {n:>3} record(s) inserted")

    print("\n  [3/3] Verifying the database ...")
    print_status()
    print_summary()

    print("  Default sign-in details")
    print("  " + "-" * 30)
    print("  Administrator : admin  / admin123")
    print("  Viewer        : viewer / viewer123")
    print()
    print("  Next step:  python -m streamlit run app.py")
    print("  (or simply double-click setup_and_start.bat)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # pragma: no cover - user facing guard
        print(f"\n  SETUP FAILED: {error}")
        sys.exit(1)
