# SpendSense — Personal Expense Intelligence

SpendSense is a single-owner expense management application. Local development uses MySQL; the optional free Render demo uses a separate temporary SQLite database. Dashboards, budgets, reports, anomaly indicators, and forecasts are calculated from the selected database's actual records. CSV imports are parsed in memory. There are no bank connections, paid APIs, or sample transactions.

## Features

- Add, edit, search, filter, sort, paginate, and delete income and expense transactions.
- Import bank-export CSV files with a preview, column mapping, validation, and duplicate detection.
- Use default and custom categories, monthly overall and category budgets, and budget warnings.
- View month-filtered dashboard totals, income, category breakdowns, budget usage, and six-month spending trends.
- Explore Pandas/NumPy spending summaries, monthly comparisons, category totals, and weekly patterns.
- Forecast next-month spending with chronological holdout evaluation using scikit-learn Linear Regression.
- Review IQR-based unusual expense indicators and month-over-month expense increases.
- Download monthly or complete transaction history as CSV.
- Responsive React interface with landing page, dashboard, and dedicated transaction, import, category, budget, analytics, prediction, unusual expense, report, and settings views.

## Technology

- Frontend: React 18, Vite, JavaScript, Tailwind CSS v4, Recharts, React Router, Axios, Lucide React.
- Backend: Python, FastAPI, Pandas, NumPy, scikit-learn, SQLAlchemy 2, PyMySQL, Pydantic.
- Database: MySQL for local use; SQLite for the optional ephemeral hosted demo.

## Architecture

```text
frontend/                 React single-page application
  src/App.jsx             Routes, page components, charts, forms
  src/api.js              Axios API client
  src/styles.css          Responsive dark finance dashboard
backend/
  app/main.py             FastAPI routes, validation, CSV workflows
  app/models.py           SQLAlchemy MySQL models
  app/schemas.py          Pydantic request/response contracts
  app/analytics.py        Pandas/NumPy analytics, ML, IQR detection
  app/database.py         MySQL engine and request-scoped sessions
  app/config.py           Environment configuration
  tests/                  Analytics and forecast tests
```

SpendSense is a single-owner workspace, not a multi-user service. Local development keeps authentication disabled by default; the Render deployment configuration enables a shared password login and fails closed unless its secrets are set. Do not expose an unauthenticated API publicly.

## Prerequisites

- Windows 11, PowerShell, Python 3.10+ (`py`), Node.js 20+, and MySQL 8+.
- A local MySQL account with permission to create/use the application database.

## MySQL setup

From the project root, run the setup script:

```powershell
.\backend\setup-mysql.ps1
```

Enter a local MySQL administrator username and password when prompted. The script creates the `spendsense` database, generates a unique application-account password, writes the ignored `backend\.env`, and verifies that the generated account can connect. The administrator password is prompted securely and is not saved. The script refuses to overwrite an existing `backend\.env`. After installing backend dependencies, start FastAPI; its startup initializes the tables and default categories.

Optional local settings:

```powershell
.\backend\setup-mysql.ps1 -MySQLHost 127.0.0.1 -MySQLPort 3306 -DatabaseName spendsense -DatabaseUser spendsense_app
```

If you prefer manual setup, create a database and a dedicated application user in MySQL with permission to select, insert, update, delete, create, alter, index, and reference tables in the database. Then copy `.env.example` to `backend\.env` and set your chosen database credentials. The app creates or initializes tables and default categories on startup.

## Environment configuration

Only needed when configuring the connection manually. The automated setup script creates this file for you.

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and, if needed, `DB_HOST`/`DB_PORT` to match your local MySQL setup. The included example frontend origin is `http://localhost:5173`.

## Installation

Open two PowerShell terminals at the project root.

Backend dependencies and tests:

```powershell
py -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
py -m pytest backend\tests -q
```

If PowerShell blocks virtual-environment activation, run commands using `backend\.venv\Scripts\python.exe` instead.

Frontend dependencies and production build:

```powershell
Set-Location frontend
npm install
npm run build
```

## Start the application

Terminal 1 — from the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:5173>. API health is available at <http://localhost:8000/api/health>, and interactive API documentation is at <http://localhost:8000/docs>. The frontend uses `http://localhost:8000/api` by default; set `VITE_API_URL` in the frontend environment before starting Vite to use a different local API URL.

If a different local app already occupies port 8000 or 5173, use free ports and configure the frontend API URL before starting Vite. For example, with the backend on port 8002, create `frontend\.env.local` with `VITE_API_URL=http://127.0.0.1:8002/api`, then run:

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

In that case, add `http://127.0.0.1:5174` to the backend `CORS_ORIGINS` setting, then restart FastAPI.

## CSV import

Export transactions as CSV from your bank without sharing bank credentials. Upload a UTF-8 `.csv` file (maximum 5 MB and 10,000 rows), review the detected columns, map date, description, amount or debit/credit, and optionally merchant/category, then confirm. Dates and amounts are validated before commit. Exact matching date/amount/description/merchant/type rows are skipped as duplicates. The original upload is not written to disk.

## API overview

- `GET /api/health`
- `GET|POST /api/transactions`, `PUT|DELETE /api/transactions/{id}`
- `GET|POST|DELETE /api/categories`
- `GET|POST|DELETE /api/budgets`
- `POST /api/imports/preview`, `POST /api/imports/confirm`
- `GET /api/dashboard`, `/api/analytics`, `/api/predictions`, `/api/anomalies`
- `GET /api/reports/monthly`, `/api/reports/export`
- OpenAPI UI: `/docs`

## Testing

Run backend analytics/ML tests:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

With the local `backend\.env` and MySQL account configured, this also runs live MySQL integration tests for transaction CRUD, search, categories, budgets, dashboard, reports, CSV import/duplicates, analytics, forecasts, and anomaly detection. The integration tests clean up the temporary data they create.

Build and validate the frontend:

```powershell
Set-Location frontend
npm run build
```

The statistical and forecast tests use synthetic, in-memory examples only. End-to-end transaction/import/budget/report tests require a configured MySQL account. Verify a local connection with `http://localhost:8000/api/health`, then exercise create/edit/delete, CSV preview/confirm, budgets, and CSV export through the UI or `/docs`.

## Free-tier deployment (Render web + static sites + temporary SQLite)

The Render Blueprint at `render.yaml` uses the DataPilot-style two-service stack: a Python web service for FastAPI and a static site for React/Vite, with free service plans. Local development continues to use the MySQL settings in `backend\.env`. The hosted API uses a separate SQLite file at `/tmp/spendsense.db`; the laptop's MySQL service and records are not copied, exposed, or modified.

**Important: this is a disposable demo database, not persistent financial storage.** Render Free web services have an ephemeral filesystem. The SQLite database is deleted when the service spins down, restarts, or redeploys. The app may also be unavailable while a free service spins back up. Do not use the hosted demo for records that must be retained. Keep important transactions in your local MySQL database and make backups. Render documents these free-instance limits at <https://render.com/docs/free>.

The application supports single-user password authentication. Render enables it and fails closed unless `APP_SECRET_KEY` and `APP_PASSWORD_HASH` are configured. Login returns a signed, expiring bearer token. Generate the production secrets locally without sending them to chat:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe -m app.auth
Set-Location ..
```

Save the first output as Render's `APP_SECRET_KEY` and the second output as `APP_PASSWORD_HASH` using the Render dashboard's secret environment-variable form. Do not commit these values or put a plaintext password into the repository.

### Deploy the DataPilot-style stack on Render

1. Connect the private GitHub repository to Render.
2. Create a Blueprint from `render.yaml`. Review the two services before applying: `spendsense-api` (Python web service, Free) and `spendsense-web` (static site, free). Do not approve paid upgrades.
3. Configure `APP_SECRET_KEY` and `APP_PASSWORD_HASH` in the API's secret environment settings. Generate the values locally as described above. Use a unique password; do not send secrets through chat or commit them.
4. The Blueprint selects `sqlite:////tmp/spendsense.db`, restricts CORS to the expected frontend origin, and sets the frontend API URL. Confirm Render assigns `https://spendsense-api.onrender.com` and `https://spendsense-web.onrender.com`; update CORS and `VITE_API_URL` if the actual names differ, then redeploy.
5. Confirm `https://<api-service>.onrender.com/api/health` reports a connected database and the web site loads. Sign in, then exercise transaction CRUD, CSV import/export, budgets, analytics, predictions, unusual expense indicators, reports, and SPA deep links.

The hosted SQLite database starts empty and is separate from local MySQL. Nothing is automatically migrated or synchronized. Free-service restarts, spin-downs, and redeploys erase the hosted SQLite file. The app remains a single-owner workspace: anyone with its shared password can change or delete all hosted demo data. Do not enter valuable or sensitive financial records there. No cloud resources are created by this documentation.

## Temporary public sharing from a Windows laptop

The root `start_all.bat` launcher runs the FastAPI API on `127.0.0.1:8002`, the Vite frontend on `127.0.0.1:5174`, and a temporary Cloudflare Quick Tunnel. The MySQL server remains local on port 3306 and is never placed in the tunnel. The Vite server proxies `/api`, `/docs`, and `/openapi.json` to FastAPI, so browsers use the same HTTPS origin and do not connect to `localhost` on the viewer's computer.

Install the official Cloudflare Tunnel Windows package once if needed:

```powershell
winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
```

From the project root, double-click `start_all.bat` or run:

```powershell
.\start_all.bat
```

On first use, the backend window prompts for a private sharing password twice. Choose at least 16 characters. The setup writes only a PBKDF2 password hash and a random signing key into the ignored `backend\.env`; it never saves the plaintext password. Keep the Backend, Frontend, and Tunnel windows open. The Tunnel window prints the temporary `https://…trycloudflare.com` link after Cloudflare connects. Share that link only with people you trust, and send the password separately through a private channel.

The app is protected by one shared password, not separate user accounts. Anyone with both the URL and password can read, import, change, and delete the same financial records. The public link can be probed by others, so use a unique strong password and never use this setup for sensitive records you are not willing to expose through a shared-owner app. API data routes require a signed login token; only health, authentication status, and login are public. The API binds to loopback and the tunnel targets only the frontend. The frontend is a development server and this temporary link is not a production hosting or availability guarantee.

To stop public access, press `Ctrl+C` in the Tunnel window or close it. The API and frontend can remain local, or their windows can also be closed. The Quick Tunnel URL is temporary and changes when a new tunnel is started. The laptop, network connection, frontend, backend, and MySQL must remain running for the link to work; shutting down or sleeping the laptop makes it unavailable. A failed laptop or internet connection does not delete database records, which remain in local MySQL.

## Screenshots

Screenshots can be added here after deployment; none are included yet.
