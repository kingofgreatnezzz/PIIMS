# DEMO DAY SCRIPT
## Police Intelligence and Information Management System (PIIMS)
### Nigeria Police Force — Oji-River Area Command

**Target duration: 12–15 minutes of demonstration + 5–10 minutes of questions.**
Total preparation time on the day: **2 minutes**.

---

## 0. BEFORE THE SUPERVISOR ARRIVES (do this 10 minutes early)

| # | Action | Why |
|---|--------|-----|
| 1 | Copy the `Popo-crud` folder to the presentation laptop (or use the laptop you already prepared) | Avoids depending on a flash drive at the last minute |
| 2 | Double-click **`setup_and_start.bat`** and wait for the browser to open | The first run takes 2–5 minutes; every later run starts in seconds |
| 3 | Sign in as `admin` / `admin123`, then **sign out again** | Proves the login works and leaves the login screen on display |
| 4 | If you changed any data while rehearsing, run `setup_and_start.bat --reset-db` once | Guarantees the exact figures quoted in this script |
| 5 | Maximise the browser, hide the bookmarks bar (`Ctrl+Shift+B`), close other tabs | A clean screen looks professional |
| 6 | Keep **this script** open on your phone or a second sheet of paper | You will not have to remember numbers |

**Figures you should be able to quote from memory (seeded database):**

| Indicator | Value |
|-----------|-------|
| Total active cases | **5** (2 Open + 3 Under Investigation, plus 1 Closed = 6 total) |
| Total arrests made | **4** |
| Wanted persons at large | **2** (3 on the register, 1 captured) |
| Officers on duty | **5** |
| Suspects on record | **8** |
| Case numbers | `OR/2026/001` … `OR/2026/006` |

> If the year on the case numbers is not 2026, that is correct behaviour — the
> system takes the year from the computer's clock.

---

## 1. OPENING (60 seconds) — what to say

> “Good morning sir/ma. My project is the **design and implementation of a Police
> Intelligence and Information Management System**, using the **Oji-River Area
> Command** as the case study.
>
> The problem I set out to solve is that case files, arrest records, suspect
> photographs and the wanted-persons register in most commands are still kept in
> paper files and exercise books. Retrieving a single record can take hours,
> records can be misfiled or lost, and there is no way to produce a consolidated
> intelligence report quickly.
>
> What I have built is a working computerised system that replaces those paper
> registers. It is running now — this is not a slide or a mock-up. I will show you
> the login, the dashboard, each register, the search facility and the
> intelligence report itself.”

**Then say the stack in one breath:**

> “It is built in **Python**, with **Streamlit** for the interface, **SQLite** for
> the database — which is built into Python, so there is no database server to
> install — **Pandas** for the data tables and **Pillow** for the suspect
> photographs. Everything is free and it runs on an ordinary laptop with no
> internet connection.”

---

## 2. THE LOGIN AND ROLE SECURITY (90 seconds) — screen 1

**Show:** the login screen you left on display.

> “Access is controlled. Every officer must sign in, and there are two levels of
> access.”

1. **Deliberately type a wrong password first** (`admin` / `wrongpass`).
   > “The system refuses the attempt and does not say whether the username or the
   > password was wrong — that stops somebody from guessing which usernames exist.”

2. Now sign in properly: `admin` / `admin123`.
   > “Passwords are not stored as text anywhere in the database. Each one is
   > hashed with **PBKDF2-HMAC-SHA256 using a random salt and 200,000 iterations**.
   > Even if somebody copied the database file, they cannot read the passwords.”

**If asked “show me the database”:** open `police_ims.db` content later with the
*User Management* page (show the `password_hash` column is unreadable), or run
`python -c "import db; print(db.fetch_all('SELECT username, password_hash FROM users'))"`.

---

## 3. THE COMMAND DASHBOARD (2 minutes) — screen 2

**Show:** the dashboard immediately after sign-in.

Point at the four cards one by one and read them aloud:

| Card | Say this |
|------|----------|
| **Total Active Cases — 5** | “Every case that is still Open or Under Investigation. The delta underneath shows how many were filed in the last 30 days.” |
| **Total Arrests Made — 4** | “Every arrest entered by the command, linked to the suspect, the officer and the case file.” |
| **Wanted Persons at Large — 2** | “This is the live wanted register — it updates the moment a suspect is captured.” |
| **Officers on Duty — 5** | “The manpower of the command across the three departments.” |

Then scroll down and point at:

* **🕒 Recent Activity** — “The last five events in the command: case filings and
  arrests, newest first. This is the command officer's morning briefing at a glance.”
* **📊 Case Status Breakdown** and **🔎 Case Distribution by Offence** — “Management
  information: how many files are open, how many are under investigation, and which
  offences are most common in Oji-River.”
* **👮 Officer Case Load** — “This shows which officers are carrying the heaviest
  caseload, so duties can be redistributed fairly.”

> “Everything on this page is calculated live from the database — nothing here is
> hard-coded.”

---

## 4. CASE FILES — THE CORE CRUD (3 minutes) — screen 3

Click **🗂️ Case Files**.

### 4a. Show the read side (30 s)
> “This is the case register. Six case files, joined automatically with the suspect
> and the investigating officer.”

Type `Kidnapping` in the search box → “It filters as I type.”
Then use **Filter by status** → choose `Open` → “Management can isolate any group.”

Click **⬇️ Download as CSV** → “Any table can be exported to Excel for further
analysis or for a monthly return.”

### 4b. Create a case (60 s) — **the most important part**
Open the **➕ New Case File** tab.

> “Watch the case number — the system suggests the next number in the
> `OR/<year>/<serial>` format automatically.”

1. Point out the suggested `OR/2026/007`.
2. Choose a suspect from the drop-down → “The suspects are drawn from the suspect
   register — you cannot type a name that does not exist, so the records cannot
   become inconsistent.”
3. Choose the investigating officer, type of offence (`Theft`), status (`Open`).
4. Type in the description: *“Theft of a generator from a shop at Oji-River Town
   main market. Matter reported by the shop owner.”*
5. Click **💾 Save Case File**.

> “The record is saved with the correct foreign-key links to the suspect and the
> officer. The dashboard figures update immediately.”

**Go back to 🏠 Dashboard and show that *Total Active Cases* is now 6.** Then return
to Case Files.

### 4c. Demonstrate validation (30 s)
Try to save a **duplicate** case number (`OR/2026/001`) and then try to save with a
**blank description**.

> “The system refuses inconsistent data. Uniqueness of the case number is enforced
> by the database itself, not only by the screen.”

### 4d. Edit and delete (40 s)
* Open **✏️ Edit Case File** → change the status of the case you created from
  `Open` to `Closed` → **Update** → “Case files are never deleted in normal
  practice; they are closed. The system tracks the status.”
* Open **🗑️ Delete Case File** → select a case → click delete.
  > “Deleting requires a **second confirmation**, and if the case has an arrest
  > attached the system warns me and asks whether the linked records should go too —
  > that is the foreign-key integrity working.”
  **Cancel the dialog** — do not actually delete during the demo unless you have
  plenty of time.

---

## 5. ARREST RECORDS (90 seconds) — screen 4

Click **🚔 Arrest Records**.

> “Arrests are the link between suspects and case files.”

1. Show the register: suspect, arresting officer with force number, linked case
   number, date, location and notes.
2. Open **➕ New Arrest** and record one:
   * Suspect: **Blessing Nwankwo**
   * Arresting Officer: **Insp. Chukwudi Eze**
   * Linked case: **OR/2026/002**
   * Location: **Ndeaboh**
   * Notes: *“Arrested at Ndeaboh main market following a tip-off; she has made a
     statement and is assisting the investigation.”*
3. Save it, then point at the dashboard again → **Total Arrests Made = 5**.

> “Notice that the arrest is linked to a **case file that already exists** — the
> system will not let you invent a case number.”

---

## 6. SUSPECT RECORDS WITH PHOTOGRAPHS (2 minutes) — screen 5

Click **🧾 Suspect Records**.

1. Show the register with the photograph column and the gallery below it.
2. Open **➕ Add Suspect** and add a real record:
   * Name: **Samuel Adeyemi**
   * Sex: **Male**, Age: **36**, Height: **1.74 m**
   * Address: **No. 21 Old Market Road, Oji-River Town**
   * Occupation: **Welder**
   * **Upload a photograph** — have a `.jpg` ready on the Desktop.
3. Save, then scroll to the gallery → the photograph is displayed.

> “The photograph is handled with **Pillow**: it is converted to JPEG, resized to a
> maximum of 600 pixels and stored in the `photos/` folder, while the path is saved
> in the database. That keeps the database small and means a corrupted or oversized
> upload cannot damage the system.”

**Strong closing line for this section:**

> “This is the feature that a paper register can never offer — the photograph of a
> suspect is attached to the record and appears automatically on the wanted-persons
> card and on the intelligence report.”

---

## 7. WANTED PERSONS REGISTER (90 seconds) — screen 6

Click **🎯 Wanted Persons**.

> “This is the public-facing part of the system — the wanted list.”

1. Show the **card layout**: photograph, name, status pill, offence, reward offered
   and last-seen location.
2. Point out that **2 are At Large** and **1 has been Captured**.
3. Click **✅ Mark as Captured** on one of the wanted persons.
   > “The moment an arrest is made, one click takes the suspect off the wanted
   > list. The dashboard indicator drops immediately — that is the real-time
   > intelligence advantage over a paper register.”
4. Optionally click **↩️ Return to At Large** to restore the original demonstration
   state before the panel looks again.

---

## 8. OFFICERS AND PERSONNEL (60 seconds) — screen 7

Click **👮 Officers & Personnel**.

1. Show the register with the **Cases Handled**, **Active Cases** and
   **Arrests Effected** columns.
2. Select an officer from **📂 Cases handled by each officer**.
   > “For any officer I can see, in one screen: how many case files he is handling,
   > how many are still active, how many arrests he has effected, and the actual
   > list of his cases. That is performance management that the command does not
   > have today.”
3. Point out the four metric cards for the selected officer.

---

## 9. SEARCH AND RETRIEVE (90 seconds) — screen 8

Click **🔍 Search & Retrieve**. This is the feature that solves the stated problem.

> “This is the heart of the project. In a paper system, finding a record means
> going through shelves. Here, one search covers everything.”

Search for **`Oji-River`** (or `Chinedu`, or `Fraud`, or `0785125`).

> “One search covers **suspect names, case numbers, officer names and force
> numbers, crime types, arrest locations and the wanted register**.”

1. Point out that the results come back **grouped into sections**, each showing how
   many matches were found.
2. Under **Suspects**, use the *“View full details of a suspect record”* drop-down
   → the full record appears with the photograph, address, occupation, case history
   and wanted status.
3. **The punchline:**
   > “To find this one record manually would take an officer several minutes of
   > walking to the registry and searching through files. Here it took less than
   > one second.”

---

## 10. THE COMPUTERIZED INTELLIGENCE REPORT (3 minutes) — screen 9

Click **📄 Intelligence Report**. **This is the deliverable that matches the project
document most closely — give it the most attention.**

1. Select the case **`OR/2026/003 — Kidnapping (Emeka Obi)`**.
2. Point at the preview and read the layout aloud:

   > “NIGERIA POLICE FORCE / Police Command Oji-River, Oji-River LGA, Enugu State /
   > COMPUTERIZED INTELLIGENCE REPORT — then the suspect's particulars: name, sex,
   > address, occupation, age, height, date and signature — then the
   > **INTELLIGENCE REPORT** section with the material evidence, the officer with
   > his force number, the date and the department. This is the exact format
   > prescribed in the project document.”

3. Show that the **Material Evidence** box is editable and already pre-filled:
   > “The system assembles the evidence from the case description and the notes of
   > every arrest recorded on that case, but the investigating officer can still
   > correct it before printing — because the officer is the authority, not the
   > software.”

4. Type your initials in **Signature / initials** — the report updates live.
5. Click **📕 Download as PDF**.

> “This produces a genuine A4 PDF document, ready for the file and for the
> signature of the officer. It is generated by a small PDF writer I built inside
> the reporting module, so **no additional library was needed** — the approved
> tech stack is untouched.”

6. Open the downloaded PDF to prove it, then also show **Download as HTML**
   (printable with `Ctrl+P`) and **Download as TXT** (the ASCII box version).

**Closing line:**

> “Twenty seconds to produce a report that currently takes an officer half an hour
> of manual typing, with no transcription errors.”

---

## 11. THE VIEWER ROLE — PROVING THE ACCESS CONTROL (60 seconds)

Sign out (sidebar → **🚪 Sign Out**), then sign in as `viewer` / `viewer123`.

1. Open **🗂️ Case Files**.
   > “Notice the blue notice: this is a read-only session.”
2. Point out that there are **no Add, Edit or Delete tabs at all** — only
   **View & Search**.
3. Point at the sidebar: **User Management is missing** entirely.
4. Show that the Viewer **can still search and generate reports** — open the
   Intelligence Report page and generate one.
5. **Important point for the panel:**
   > “The restriction is not only cosmetic. The write functions check the role on
   > the server side as well, so even a Viewer who tampered with the browser cannot
   > change a record.”

---

## 12. CLOSING STATEMENT (30 seconds) — what to say

> “To summarise: the system provides a secured, role-based, computerised
> alternative to the paper registers of the Oji-River Area Command.
>
> It covers **case files, arrests, suspects, wanted persons, officers and user
> accounts**, with **full create, read, update and delete** operations, a
> **command-wide search**, and the **computerized intelligence report in the exact
> prescribed format** with PDF output.
>
> It is built entirely on free and open tools, it needs no internet connection and
> no database server, it is protected against SQL injection, it stores passwords as
> salted hashes, and it enforces referential integrity in the database.
>
> Thank you sir/ma. I am ready for your questions.”

---

## 13. QUESTIONS AND ANSWERS — PREPARED RESPONSES

### Database and data

**Q: Why SQLite and not MySQL or SQL Server?**
> “SQLite is built into Python, so there is nothing to install and nothing to
> configure on the command's computers — which matters in a station where there may
> be no dedicated server or IT support. It fully supports the relationships,
> constraints and transactions this system needs, it is the most widely deployed
> database engine in the world, and the whole command database is a single portable
> file that can be backed up on a flash drive. If the command later grows, the SQL
> used here is standard and can be migrated to MySQL with minimal change.”

**Q: Where is the data stored?**
> “In a single file called `police_ims.db` in the application folder. It can be
> copied for backup, and it can be opened with any SQLite tool for audit.”

**Q: What happens if two officers use it at the same time?**
> “Streamlit serves several browser sessions at once and SQLite handles concurrent
> access with locking. Every query uses its own short-lived connection, which is the
> recommended pattern for a web application.”

**Q: How do you prevent duplicate records?**
> “Uniqueness is enforced at the database level — the case number, the officer
> number and the username all carry `UNIQUE` constraints, so a duplicate is
> rejected even if it bypassed the screen.”

### Security

**Q: Are the passwords safe?**
> “They are never stored. Each password is hashed with PBKDF2-HMAC-SHA256 using a
> random 16-byte salt and 200,000 iterations, and verified with a constant-time
> comparison. Two users with the same password get different hashes.”

**Q: Can somebody inject SQL through the search box?**
> “No. Every statement uses parameter binding with `?` placeholders, so user input
> is never concatenated into SQL. Table names that are chosen dynamically are
> validated against a whitelist. I can demonstrate it — typing
> `' OR '1'='1` in the search box simply returns no results.”

**Q: Can a Viewer change data by editing the page in the browser?**
> “No. The role is checked in the server-side function before any write, so hiding
> the buttons is only the visible half of the control.”

**Q: What about the photographs — could somebody upload a virus?**
> “Uploads are restricted to image types, then re-encoded through Pillow into a
> fresh JPEG. Only pixel data survives that process, and the file is renamed by the
> system, so an executable cannot be smuggled in and the original filename is
> discarded.”

### Design and implementation

**Q: Why one single file, `app.py`?**
> “Each page is a separate function, and the reusable logic sits in the helper
> modules — `auth.py` for security, `db.py` for the database and `reports.py` for
> the report. Keeping the pages in one file makes the application easy to deploy
> and to follow during a demonstration, while the modules keep the concerns
> separated.”

**Q: How did you test it?**
> “There is an automated suite, `test_app.py`, with 123 checks. It verifies the
> database, the password hashing, the report output — including the internal
> structure of the generated PDF — and it drives the actual interface using
> Streamlit's official test harness: signing in with good and bad credentials,
> opening all nine pages, creating a suspect and a case file through the interface,
> duplicate and blank-field validation, the Viewer restrictions and signing out. I
> can run it now.” *(You may run `python test_app.py` — it takes about a minute.)*

**Q: Is the intelligence report exactly the format required?**
> “Yes — it is reproduced line by line: the three command headings, the suspect
> particulars block with name, sex, address, occupation, age, height, date and
> signature, and the intelligence report block with material evidence, officer,
> date and department. The TXT export shows the same layout in the boxed form used
> in the project document.”

**Q: What are the limitations, and what would you add next?**
> “Three honest limitations. First, the system currently runs on a single computer
> or a local network; a full command-wide deployment would need a central server
> and a login audit trail. Second, the material evidence is typed by the officer
> rather than attached as a scanned exhibit — file attachments would be the next
> feature. Third, there is no offline mobile application yet for officers in the
> field. All three are natural extensions of the design I have presented.”

### Demonstration risk questions

**Q: What if the internet is not available?**
> “Only the first installation needs the internet, to download Streamlit, Pandas
> and Pillow. After that the system runs completely offline — which I can prove by
> disconnecting now.”

**Q: What if the laptop fails during the presentation?**
> “The whole project is a single folder that can be copied on a flash drive, and
> `setup_and_start.bat` rebuilds everything automatically on any Windows computer
> with Python installed.”

---

## 14. DEMO CHECKLIST (tick before you present)

- [ ] `setup_and_start.bat` run and the browser open at <http://localhost:8501>
- [ ] Signed in once as `admin`, signed out, login screen displayed
- [ ] A `.jpg` photograph on the Desktop for the suspect upload
- [ ] This script printed or open on a phone
- [ ] A **PDF reader** installed and tested (to open the downloaded report)
- [ ] Database reset (`--reset-db`) if you rehearsed on it
- [ ] Phone on silent, notifications off, other browser tabs closed
- [ ] Know the four dashboard figures by heart: **5 · 4 · 2 · 5**
- [ ] Practise the words “this is a working system, not a mock-up” once more
