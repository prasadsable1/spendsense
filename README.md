# SpendSense — Personal Expense Intelligence

SpendSense is a local, single-user expense management application. It records transactions in MySQL and calculates dashboards, budgets, reports, anomaly indicators, and forecasts from those records. CSV imports are parsed in memory. There are no bank connections, paid APIs, cloud services, or sample transactions.

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

This version is a local, single-user workspace and does not implement login or multi-user access. Keep the API on a trusted local network. Do not expose it publicly without adding authentication and authorization.

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

## Deployment preparation

The app is intended for local use. Before any deployment, configure a restricted database user, TLS, a production CORS allowlist, secrets management, authentication/authorization, database migrations, backups, rate limits, and production-grade upload handling. Do not expose the unauthenticated API to an untrusted network. No deployment is performed by this project setup.
