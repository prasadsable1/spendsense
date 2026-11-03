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

## Free-tier deployment (Cloudflare Pages + Render + hosted MySQL)

The Render Blueprint at `render.yaml` prepares a free Render web service for the API. It requires a separate, remotely accessible **MySQL** server. Render's free plan does not provide a persistent MySQL database or disk, and the MySQL instance on your development PC is not reachable by Render. Do not expose your PC's MySQL port to the public internet. OCI MySQL HeatWave Always Free is one possible MySQL provider; verify its current terms and card-verification requirements directly with OCI before creating an account or service.

The application now supports optional single-user password authentication. Render enables it and fails closed unless all of `APP_SECRET_KEY`, `APP_PASSWORD_HASH`, and database settings are present. Login returns a signed, expiring bearer token. Generate the production secrets locally without sending them to chat:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe -m app.auth
Set-Location ..
```

Save the first output as Render's `APP_SECRET_KEY` and the second output as `APP_PASSWORD_HASH` using the Render dashboard's secret environment-variable form. Do not commit these values or put a plaintext password into the repository.

### Deploy FastAPI on Render

1. Provision compatible hosted MySQL. Keep its hostname private and restrict access to the Render API service wherever the provider supports network restrictions.
2. In Render, create a Blueprint from the private GitHub repository and approve the `render.yaml` web service. Select the **Free** plan; do not approve a paid upgrade.
3. Configure the Blueprint's `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `CORS_ORIGINS` prompted secret/environment values. The last value must be the exact HTTPS Cloudflare Pages origin after creating the Pages project. Configure the generated `APP_SECRET_KEY` and `APP_PASSWORD_HASH` as described above.
4. If the hosted MySQL provider requires an inbound network allowlist, allow only its published Render egress ranges and port. Never open MySQL to all internet addresses.
5. Confirm the Render service starts and `https://<render-service>.onrender.com/api/health` returns a connected database status before deploying the frontend. A failed DB connection must be fixed in the provider settings, not replaced with SQLite or fake data.

The Render free web service can sleep while idle and take time to wake. Free services are not a production availability guarantee.

### Deploy React on Cloudflare Pages

1. Create a Pages project from the GitHub repository.
2. Set the project root/build directory to `frontend`, build command to `npm run build`, and output directory to `dist`.
3. Set the Pages build environment variable `VITE_API_URL` to `https://<render-service>.onrender.com/api`.
4. Deploy and note the exact Pages HTTPS origin (for example `https://<project>.pages.dev`). Add that origin to Render's `CORS_ORIGINS`, save, and redeploy/restart the API.
5. Open the Pages URL; verify the password screen, login, API-backed pages, CSV import/export, and `/api/health`. The `frontend/public/_redirects` file enables client-side route fallback.

The app remains a single-owner workspace: a shared password protects records, but this is not multi-user authorization. Use a unique long password, keep both providers' secrets private, and configure scheduled database backups before entering important financial records. No resource is created by these instructions. Provider terms, free quotas, availability, and verification requirements can change; confirm them before provisioning.

## Screenshots

Screenshots can be added here after deployment; none are included yet.
