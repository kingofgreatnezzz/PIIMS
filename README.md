# POLICE INTELLIGENCE AND INFORMATION MANAGEMENT SYSTEM (PIIMS)

**Nigeria Police Force — Police Command Oji-River, Oji-River LGA, Enugu State**

A complete, working, demo-ready web application for recording and retrieving police
intelligence: case files, arrests, suspects, wanted persons, officers and the
computerized intelligence report.

Built strictly with the approved stack — **Python 3.10+ · Streamlit · SQLite ·
Pandas · Pillow**. No paid services, no external APIs, no third-party database
server. Everything runs on one ordinary Windows laptop.

---

## 1. PROJECT FOLDER STRUCTURE

```
Popo-crud/                          <- the project folder (any location will do)
│
├── app.py                     ★ MAIN APPLICATION - all pages, CRUD, search, report
├── auth.py                    ★ Password hashing, login and role handling
├── db.py                      ★ Database layer: schema, connection, query helpers
├── reports.py                 ★ Intelligence report generator (HTML / PDF / TXT)
├── setup_db.py                ★ Creates the tables and seeds the Oji-River sample data
├── requirements.txt           ★ Exact list of packages needed
├── setup_and_start.bat        ★ ONE-CLICK WINDOWS LAUNCHER (create venv, install,
│                                build database, start the app)
│
├── test_app.py                  Automated verification suite (123 checks)
├── README.md                    This file
├── DEMO_SCRIPT.md               Step-by-step presentation guide for the defence
├── DEPLOYMENT_GUIDE.md          How to push to GitHub / deploy on Streamlit Cloud
├── .gitignore                   Files that should not be committed
│
├── .streamlit/
│   └── config.toml              Command colours, upload limit, browser settings
│
├── photos/                      Suspect photographs uploaded through the app
│   └── suspect_0001_1789....jpg
│
└── police_ims.db                The SQLite database (created by setup_db.py)
```

Everything marked ★ is a file you can open and explain during the presentation.

---

## 2. QUICK START (WINDOWS)

### Option A — the automatic way (recommended)

1. Copy the whole `Popo-crud` folder to the presentation computer.
2. Double-click **`setup_and_start.bat`**.

The script will automatically:

| Step | What happens |
|------|--------------|
| 1 | Find a Python 3 interpreter on the computer |
| 2 | Create the `venv` virtual environment if it does not exist |
| 3 | Activate the virtual environment (and bootstrap `pip` if necessary) |
| 4 | Install everything in `requirements.txt` (Streamlit, Pandas, Pillow) |
| 5 | Build and seed `police_ims.db` if the database file is missing |
| 6 | Start the application and open the browser at <http://localhost:8501> |

Optional switches:

```bat
setup_and_start.bat --reinstall     force a fresh installation of the packages
setup_and_start.bat --reset-db      rebuild and reseed the database
setup_and_start.bat --port 8502     run on another port (if 8501 is busy)
setup_and_start.bat --help          show the help screen
```

### Option B — the manual way

```bat
cd Popo-crud
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python setup_db.py
streamlit run app.py
```

> If `venv\Scripts\activate` is not recognised (this can happen when the
> environment was created by a tool other than the `venv` module), you do not
> need it — every command can be run through the interpreter directly:
>
> ```bat
> venv\Scripts\python.exe -m pip install -r requirements.txt
> venv\Scripts\python.exe setup_db.py
> venv\Scripts\python.exe -m streamlit run app.py
> ```

### Option C — macOS / Linux (for reference)

```bash
cd Popo-crud
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup_db.py
streamlit run app.py
```

---

## 3. SIGN-IN DETAILS

| Role | Username | Password | Privileges |
|------|----------|----------|------------|
| **Administrator** | `admin` | `admin123` | Add, edit, delete, view, search, generate reports, manage user accounts |
| **Viewer** | `viewer` | `viewer123` | View, filter, search and generate reports only — every add/edit/delete control is hidden |

Passwords are never stored in clear text. Each one is hashed with
**PBKDF2-HMAC-SHA256, 200 000 iterations and a random 16-byte salt**
(`hashlib` from the Python standard library), and verified with
`hmac.compare_digest` to prevent timing attacks.

---

## 4. FEATURES AND WHERE TO FIND THEM

| Page | What it does |
|------|--------------|
| 🏠 **Command Dashboard** | Four `st.metric` indicator cards (active cases, arrests, wanted persons at large, officers on duty), a recent-activity feed of the last five cases/arrests, a case-status breakdown chart, an offence-distribution chart and an officer case-load table |
| 🗂️ **Case Files** | Full CRUD with search, status filter and offence filter; automatic `OR/<year>/<serial>` case-number suggestion; full case detail panel with the linked suspect, officer and arrests |
| 🚔 **Arrest Records** | Full CRUD, arrests linked to a suspect, an officer and a case file; search, location filter and an arrest detail panel |
| 🎯 **Wanted Persons** | Card layout with the suspect's photograph, reward, last-seen location and status; one-click *Mark as Captured* / *Return to At Large*; search and status filter |
| 👮 **Officers & Personnel** | Full CRUD, department filter, and a per-officer caseload analysis (cases handled, active files, arrests effected, list of assigned cases) |
| 🧾 **Suspect Records** | Full CRUD with photograph upload (Pillow resizes and stores it in `photos/`), photograph gallery, case history per suspect |
| 🔍 **Search & Retrieve** | One search box that searches suspect names, case numbers, officer names *and* force numbers, crime types, arrest locations and wanted entries — results grouped into expandable sections with a "view full details" panel for each hit |
| 📄 **Intelligence Report** | Select a case, edit the material evidence, and print the report in the exact prescribed format. Download as **PDF**, HTML or TXT |
| 👥 **User Management** | *Administrators only.* Create accounts, reset passwords and delete accounts (the last administrator can never be deleted) |

Every list can be downloaded as CSV for further analysis.

---

## 5. THE INTELLIGENCE REPORT

Generated on the **📄 Intelligence Report** page in the exact layout required by
the project document:

```
┌─────────────────────────────────────────────────────────────┐
│ NIGERIA POLICE FORCE                                        │
│ Police Command Oji-River, Oji-River LGA, Enugu State        │
│ COMPUTERIZED INTELLIGENCE REPORT                            │
├─────────────────────────────────────────────────────────────┤
│ Name of Suspect: [Name]        Sex: [M/F]                   │
│ Address: [Address]             Occupation: [Occupation]     │
│ Age: [Age]                     Height: [Height]             │
│ Date: [Date]                   Sign: [Signature/Initials]   │
├─────────────────────────────────────────────────────────────┤
│ INTELLIGENCE REPORT                                         │
│ Material Evidence: [Description of evidence]                │
│ Officer: [Officer Name & Number]                            │
│ Date: [Report Date]                                         │
│ Department: [Department Name]                               │
└─────────────────────────────────────────────────────────────┘
```

* The **Material Evidence** field is pre-filled from the case description and the
  notes of every linked arrest, and remains editable before printing.
* **Download as PDF** produces a genuine A4 PDF. It is written by a small
  built-in PDF writer inside `reports.py`, so **no extra PDF library is needed** —
  the approved stack stays untouched.
* **Download as HTML** produces a print-ready document: open it and press
  `Ctrl+P` to obtain a hard copy. **Download as TXT** produces the ASCII box
  version shown above.
* A footer line carries the case reference, offence, status, arrest summary and
  the operator who generated the report, for audit purposes.

---

## 6. DATABASE

SQLite, single file `police_ims.db`, created by `setup_db.py`. Foreign keys are
enforced (`PRAGMA foreign_keys = ON`) on every connection.

| Table | Purpose | Key relationships |
|-------|---------|-------------------|
| `users` | Application accounts | — |
| `officers` | Personnel of the command | — |
| `suspects` | Persons of interest (+ photograph) | — |
| `cases` | Case files | → `suspects`, → `officers` |
| `arrests` | Arrest records | → `suspects`, → `officers`, → `cases` |
| `wanted_persons` | Wanted register | → `suspects` |

All `CHECK` constraints from the specification are implemented (sex `M`/`F`,
department list, case status list, wanted-status list, user role list).

### Seeded demonstration data (`python setup_db.py --reset`)

| Table | Records |
|-------|---------|
| users | 2 — one Administrator, one Viewer |
| officers | 5 — Intelligence, Crime Investigation, Fraud Investigation |
| suspects | 8 — varied sexes, ages, occupations and addresses |
| cases | 6 — 2 Open, 3 Under Investigation, 1 Closed |
| arrests | 4 — each linked to a suspect, an officer and a case |
| wanted_persons | 3 — 2 *At Large*, 1 *Captured* |

Offences used: Armed Robbery, Fraud, Assault, Theft, Kidnapping.
Locations used: Oji-River Town, Ndeaboh, Agbani, Udi, Akegbe Ugwu.
Officer numbers follow the `0785124` format and case numbers the
`OR/2026/001` format (the year is taken from the system clock, so the
prefix always matches the current year).

> **Deleting records.** Because the foreign keys are enforced, a suspect who is
> still referenced by a case or an arrest cannot be deleted silently. The
> confirmation dialog detects the linked records, lists them and offers an
> explicit *cascade delete* tick box. Nothing is ever removed without a second
> confirmation.

---

## 7. AUTOMATED TESTS

```bat
venv\Scripts\python.exe test_app.py
```

*(If you have activated the virtual environment, plain `python test_app.py` works
just as well.)*

The suite rebuilds the demonstration database and runs **123 checks**:

* database layer — table creation, seeding, foreign keys, parameterised queries,
  identifier validation;
* authentication — PBKDF2 format, salt uniqueness, correct/incorrect passwords,
  malformed hashes, role resolution, protection of the last administrator;
* report generation — every prescribed report line, HTML validity, PDF structure
  (header, object table, cross-reference offsets, font resources);
* the Streamlit application itself, driven through Streamlit's official
  `AppTest` harness — sign-in with good and bad credentials, all nine pages
  rendering without exception, creating a suspect and a case file through the
  UI, duplicate and blank-field validation, search, the Viewer read-only
  restrictions and signing out;
* photograph handling — JPEG normalisation, resizing, data-URI embedding;
* data integrity — no orphan records, `CHECK` constraints actually enforced.

Expected result: `Checks run: 123, Passed: 123, Failed: 0`.

---

## 8. TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| `python` is not recognised | Reinstall Python 3.10+ and tick **"Add python.exe to PATH"** |
| Port 8501 already in use | `setup_and_start.bat --port 8502` |
| The dashboard shows no figures | Run `python setup_db.py --reset` |
| Streamlit reports a missing package | Run `setup_and_start.bat --reinstall` |
| Photographs do not appear | Confirm the `photos/` folder exists beside `app.py`; it is recreated automatically by `setup_db.py` |
| A dependency install fails | Check the internet connection; the first run downloads about 60 MB |
| The browser does not open | Open <http://localhost:8501> manually |
| `venv` was copied from another computer | Delete the `venv` folder and run `setup_and_start.bat` again — it will build a fresh environment for this machine |
| `venv\Scripts\activate` is not recognised | Use `venv\Scripts\python.exe` directly, as shown in section 2, Option B |

---

## 9. SECURITY NOTES (worth mentioning to the panel)

1. Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes — never in clear text.
2. Every SQL statement uses parameter binding (`?`), which structurally prevents
   SQL injection; dynamic table names are checked against a whitelist.
3. Role checks are enforced **server-side** on every write operation
   (`auth.require_admin()`); the Viewer interface merely hides the controls.
4. Failed sign-in attempts are counted per session to slow down guessing.
5. Foreign-key integrity prevents orphan records, and deletions require explicit
   confirmation.
6. Photographs are normalised and resized before storage, so a malicious or
   corrupted upload cannot be executed or bloat the database.

---

**© Nigeria Police Force — Oji-River Area Command · PIIMS v1.0**
"# PIIMS" 
