# DEPLOYMENT GUIDE
## PIIMS — Police Intelligence and Information Management System
### Nigeria Police Force, Oji-River Area Command

This guide covers three things:

1. **Part A** — Publishing the project on **GitHub** (your source code repository)
2. **Part B** — Deploying the live application on **Streamlit Community Cloud** (free)
3. **Part C** — Sharing the live link with your supervisor, plus a maintenance section

Everything described here uses **free tiers only**. No credit card is required.

---

## PART A — PUSH THE PROJECT TO GITHUB

### A1. Before you push (clean the folder)

The virtual environment must **never** be committed — it contains thousands of
files and hundreds of megabytes. The `.gitignore` file in this project already
excludes it. Confirm it contains:

```gitignore
venv/
__pycache__/
*.pyc
.deps_ok
```

> **Important decision about the database.** `police_ims.db` and the `photos/`
> folder are **data**, and they *are* committed deliberately, so that the live
> demo on the internet opens with the Oji-River sample data instead of an empty
> system. If you prefer not to publish the sample data, add
> `police_ims.db` to `.gitignore` — the application will then show its
> *“System Setup Required”* screen, where a single button rebuilds and seeds the
> database.

### A2. Create the repository on GitHub

1. Sign in at <https://github.com> (create a free account if necessary — use a
   professional username, your supervisor will see it).
2. Click the **+** in the top-right corner → **New repository**.
3. Fill in:
   * **Repository name:** `police-intelligence-management-system`
     *(or `popo-crud` to match your folder)*
   * **Description:** `Police Intelligence and Information Management System — Nigeria Police Force, Oji-River Area Command (Python · Streamlit · SQLite)`
   * **Visibility:** **Public** (required — Streamlit Community Cloud deploys
     free apps only from public repositories). Choose *Private* only if your
     supervisor insists, and note that you would then need a paid Streamlit plan.
   * **Do NOT** tick “Add a README file”, “Add .gitignore” or “Choose a licence”
     — you already have these.
4. Click **Create repository**.
5. Copy the repository URL shown, e.g.
   `https://github.com/YOUR-USERNAME/police-intelligence-management-system.git`

### A3. Push from your computer

Open **Command Prompt** or **PowerShell** in the project folder and run the
commands below one at a time.

```bat
cd C:\Users\TECHDEBIA\Documents\pro\Popo-crud

git init
git branch -M main
git config user.name  "Your Full Name"
git config user.email "your.email@example.com"

git add .
git status
```

**Read the `git status` output before continuing.** Check that `venv/` is *not*
listed. If it is, `.gitignore` is missing or in the wrong folder.

```bat
git commit -m "PIIMS: Police Intelligence and Information Management System (Oji-River Area Command)"
git remote add origin https://github.com/YOUR-USERNAME/police-intelligence-management-system.git
git push -u origin main
```

When prompted, sign in to GitHub. If Git asks for a password, GitHub requires a
**Personal Access Token** instead:

> GitHub → your picture → **Settings** → **Developer settings** →
> **Personal access tokens** → **Tokens (classic)** → **Generate new token
> (classic)** → tick **repo** → **Generate** → copy the token and paste it as the
> password.

### A4. Verify

Refresh the repository page. You should see `app.py`, `db.py`, `auth.py`,
`reports.py`, `setup_db.py`, `setup_and_start.bat`, `requirements.txt` and the
`photos/` folder — and **no `venv/` folder**.

### A5. Later updates

Every time you change something:

```bat
git add .
git commit -m "Describe what you changed"
git push
```

Streamlit Cloud redeploys automatically within a minute of each push.

---

## PART B — DEPLOY ON STREAMLIT COMMUNITY CLOUD (FREE)

Streamlit Community Cloud hosts the application on the internet free of charge,
straight from your GitHub repository.

### B1. Create the account

1. Go to <https://share.streamlit.io>
2. Click **Continue with GitHub** and authorise Streamlit (it needs read access
   to your repositories).
3. Complete the short profile form.

### B2. Deploy the app

1. Click **Create app** (or **New app**).
2. Choose **Deploy a public app from GitHub** and fill in:

   | Field | Value |
   |-------|-------|
   | **Repository** | `YOUR-USERNAME/police-intelligence-management-system` |
   | **Branch** | `main` |
   | **Main file path** | `app.py` |
   | **App URL** | choose something meaningful, e.g. `npf-oji-river-piims` |

3. *(Optional)* Click **Advanced settings** and set **Python version** to
   **3.11**.
4. Click **Deploy**.

The first deployment takes **3–5 minutes** while Streamlit installs `requirements.txt`.
You will see the build log scrolling; when it finishes, the login screen appears.

Your application is now live at:

```
https://npf-oji-river-piims.streamlit.app
```

### B3. Close the browser's “Are you sure?” prompt (optional but recommended)

Streamlit Cloud puts an idle app to sleep. When the supervisor opens the link it
may show a **“Yes, get this app back up!”** button — which looks unprofessional.
To avoid this during your defence, simply open the link yourself 10 minutes
before the presentation. A **free** account cannot disable sleeping entirely, but
visiting the app wakes it in about 30 seconds.

### B4. If the app shows the “System Setup Required” screen

This means the database file was not included in the repository. This is not a
failure — press the **🔧 Initialise the database now** button on that screen. The
tables and the Oji-River sample data will be created in the cloud instance within
a few seconds, and the system is ready.

> Note: Streamlit Cloud containers restart periodically, and any data you enter
> in the cloud demo is discarded when that happens. The cloud link is excellent
> for **showing** the system to your supervisor; the **local installation**
> (`setup_and_start.bat`) is the real, permanent command database.

### B5. Managing the app

* **Reboot:** Streamlit Cloud → your app → **⋮** menu → **Reboot app**
* **Delete:** **⋮** menu → **Delete app**
* **Change settings:** **⋮** menu → **Settings**
* **Logs:** the right-hand panel shows the live log; use it if a deployment fails

---

## PART C — SHARING THE LINK AND MAINTAINING THE SYSTEM

### C1. The message to send your supervisor

> Good day sir/ma.
>
> The Police Intelligence and Information Management System has been deployed and
> is available online at:
>
> **https://npf-oji-river-piims.streamlit.app**
>
> Sign-in details:
> * Administrator — username `admin`, password `admin123`
> * Viewer (read only) — username `viewer`, password `viewer123`
>
> Please begin with the Administrator account: the dashboard shows the command
> indicators, and the *Intelligence Report* page generates the prescribed report
> as a PDF. Signing in as `viewer` demonstrates the read-only restriction.
>
> The source code is at:
> **https://github.com/YOUR-USERNAME/police-intelligence-management-system**
>
> Thank you.

### C2. Screenshots for the written report

Capture these six screens in the order below — they map directly onto the
chapters of your project document:

| # | Screen | Caption for the report |
|---|--------|------------------------|
| 1 | Login page | *Figure 4.1 — Secured sign-in screen with role-based access* |
| 2 | Dashboard | *Figure 4.2 — Command dashboard showing the four key indicators* |
| 3 | Case Files register | *Figure 4.3 — Case file management with search and filters* |
| 4 | Suspect records with photographs | *Figure 4.4 — Suspect register with photographic records* |
| 5 | Wanted persons cards | *Figure 4.5 — Wanted persons register* |
| 6 | Intelligence report preview + PDF | *Figure 4.6 — Computerized intelligence report in the prescribed format* |
| 7 *(bonus)* | Viewer session | *Figure 4.7 — Read-only Viewer session with write controls hidden* |

### C3. Backing up the command database

The entire system data lives in one file:

```bat
copy police_ims.db "D:\Backups\police_ims_%date:~-4%%date:~3,2%%date:~0,2%.db"
```

Also copy the `photos/` folder — it holds the suspect photographs referenced by
the database.

### C4. Routine maintenance

| Task | Command |
|------|---------|
| Start the system | double-click `setup_and_start.bat` |
| Update the packages | `setup_and_start.bat --reinstall` |
| Rebuild the sample data | `setup_and_start.bat --reset-db` |
| Run the 123 automated checks | `venv\Scripts\python.exe test_app.py` |
| Change the port | `setup_and_start.bat --port 8502` |
| Inspect the database counts | `python setup_db.py --status` |

### C5. Hardening before real deployment at the command

The following changes are recommended before the system is used with real police
records (mention them as future work in your report):

1. **Change the default passwords** immediately after installation — use
   *User Management → Reset Password*.
2. **Remove the demonstration credentials block** from the login page
   (`render_login()` in `app.py`).
3. **Serve over HTTPS** on the command's local network, and keep the server in a
   locked office.
4. **Schedule automatic backups** of `police_ims.db` and `photos/` to an external
   drive or the command's network share.
5. **Add an audit trail table** recording every insert, update and delete with the
   operator's username and timestamp. *(Good answer if the panel asks what you
   would do next.)*
6. **Consider MySQL/PostgreSQL** if several Area Commands must share one central
   database; the SQL used in `db.py` is standard and migrates with little change.

---

## PART D — TROUBLESHOOTING THE DEPLOYMENT

| Symptom | Cause and fix |
|---------|---------------|
| Deployment fails with `ModuleNotFoundError` | A package is missing from `requirements.txt`, or the file was not pushed. Confirm it lists `streamlit`, `pandas`, `Pillow` |
| `Repository not found` on Streamlit Cloud | The repository is **private**. Make it public (Settings → General → Danger zone → Change visibility) |
| `Error installing requirements` | Usually a typo in `requirements.txt`; check the build log for the exact package |
| The app is asleep / slow to open | Normal on the free tier. Open the link a few minutes early, or press *“Yes, get this app back up!”* |
| Data typed in the cloud disappears later | Expected — cloud storage is temporary. Use the local installation for real records |
| The app runs locally but not in the cloud | Check that `app.py` is in the root of the repository, not inside a sub-folder |
| Photographs do not show in the cloud | The `photos/` folder was not committed, or the photograph was uploaded to a cloud session that has since restarted |

---

**© Nigeria Police Force — Oji-River Area Command · PIIMS v1.0**
