# SpendSense — Personal Expense Intelligence

SpendSense is a single-owner expense management application. It records transactions in MySQL and calculates dashboards, budgets, reports, anomaly indicators, and forecasts from those records. CSV imports are parsed in memory. There are no bank connections, paid APIs, or sample transactions. The app can run locally or be deployed using the optional free-tier configuration below.

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
- Database: MySQL.

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

## Free-tier deployment (Render web + static sites + hosted MySQL)

The Render Blueprint at `render.yaml` defines the same two-service shape as DataPilot: a Python web service for FastAPI and a static site for the React/Vite frontend. Both are configured for free tiers. The API requires a separately provisioned, remotely accessible **MySQL** server. Render does not provide a free persistent MySQL database, and a MySQL server on your development PC (`127.0.0.1`) cannot be reached by Render. Do not expose your PC's MySQL port to the public internet or replace MySQL with another database. OCI MySQL HeatWave Always Free may be an option; independently verify its current terms, capacity, and identity/card-verification requirements before creating resources.

The application now supports optional single-user password authentication. Render enables it and fails closed unless all of `APP_SECRET_KEY`, `APP_PASSWORD_HASH`, and database settings are present. Login returns a signed, expiring bearer token. Generate the production secrets locally without sending them to chat:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe -m app.auth
Set-Location ..
```

Save the first output as Render's `APP_SECRET_KEY` and the second output as `APP_PASSWORD_HASH` using the Render dashboard's secret environment-variable form. Do not commit these values or put a plaintext password into the repository.

### Deploy the DataPilot-style stack on Render

1. Provision MySQL with a provider that allows secure connections from Render. Create a dedicated, non-root SpendSense user with permission only on the SpendSense database. Keep credentials private. Never expose a laptop's MySQL server to the internet.
2. In Render, create a Blueprint from the private GitHub repository and review both resources before applying: `spendsense-api` (Python web service, Free) and `spendsense-web` (static site, free). Do not approve any paid plan or upgrade.
3. Configure the API's `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `APP_SECRET_KEY`, `APP_PASSWORD_HASH`, and `CORS_ORIGINS` values in Render's environment settings. The CORS origin must be the static site's exact HTTPS origin. Generate the authentication secrets locally as described above; do not paste them into chat or commit them.
4. Configure the static site's `VITE_API_URL` to the API's exact HTTPS base URL ending in `/api`. Because Vite embeds this value at build time, redeploy the static site after changing it. The API URL and web origin may use `spendsense-api.onrender.com` and `spendsense-web.onrender.com` if those names are assigned; verify the actual service URLs in the Render dashboard.
5. If the MySQL provider requires an IP allowlist, allow only the provider-supported Render egress addresses and database port. Do not open MySQL to all internet addresses. Confirm `https://<api-service>.onrender.com/api/health` returns a connected database before checking the frontend.
6. Confirm the web service loads, login succeeds, and transactions, CSV import/export, budgets, analytics, forecasts, anomaly indicators, and reports use the hosted MySQL data. Confirm SPA deep links work.

Render's free web service may sleep while idle and is not an availability guarantee. The application is still a single-owner workspace: one shared password protects the records; there are no separate user accounts. Configure database backups before entering important financial records. Never enter production credentials in a public issue or chat. No cloud resources are created by this documentation; verify current provider pricing and terms before provisioning.

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
