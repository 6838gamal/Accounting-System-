# نظام المحاسبة السحابي

A cloud-based Arabic accounting system built with FastAPI, SQLAlchemy, and Bootstrap 5.

## Stack

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.x
- **Templates**: Jinja2 + Bootstrap 5 (RTL/Arabic)
- **Database**: SQLite (`accounting.db`) with Alembic migrations
- **Auth**: Session-based (itsdangerous)
- **PDF**: ReportLab / xhtml2pdf / WeasyPrint
- **Excel**: OpenPyXL
- **Charts**: Chart.js

## How to run

```bash
python main.py
```

App runs on port 5000. Default login: **admin / admin123**

## Environment variables required

| Variable | Description |
|---|---|
| `SECRET_KEY` | App HMAC secret (auto-generated for dev) |
| `SESSION_SECRET` | Session signing key (≥32 chars) |

## Key routes

- `/` → dashboard
- `/contracts` → contract list
- `/contracts/{id}` → contract detail
- `/contracts/{id}/print` → print view (right sig + left sig + stamp centre)
- `/contracts/{id}/layout-editor` → layout editor (company signature only, right-aligned)
- `/contracts/{id}/pdf` → download PDF

## Contract signature layout

- **Print / طباعة**: Three-part footer — company signature (right), client signature (left), stamp (centre).
- **Layout editor / محرر**: Only the company (first-party) signature shown, right-aligned. Stamp not shown in editor.
- **PDF**: Controlled by `show_signatures` flag; two-column signature table in `app/templates/pdf/contract.html`.

## User preferences

- Keep existing project structure — do not restructure or migrate.
- Arabic RTL layout throughout.
