# Caregiver Management System Backend

Local Flask and SQLite backend for the existing CareCircle frontend. No caregiver data is sent to a cloud service.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

The database is created automatically at `database/caregivers.db`.

## APIs

- `POST /upload` — multipart field `file`; accepts `.csv`, `.xls`, `.xlsx`.
- `GET /dashboard` — dashboard counts, alerts, and chart distributions.
- `GET /analytics` — analytics report.
- `GET /caregivers` — supports `search`, `language`, `centre`, `hobby`, `need`, `flag`, `page`, `per_page`, `sort_by`, and `sort_direction`.
- `GET /caregiver/<id>` — complete caregiver profile.
- `GET /alerts` — birthdays, grant follow-ups, and overdue check-ins.
- `POST /recommendations` — JSON body with `workshop`, optional `language`, `interests`, `caregiving_domain`, `centre`, and `maximum_participants`.

## Import columns

Required: `Name`, `Phone No`.

Optional: `Situation`, `Grants`, `Needs`, `Hobbies`, `Language`, `Birthday`, `ZBI`, `Centre`, `Check When`, `Check What`, `Flag`. Extra columns are ignored. Imports update an existing record when `Name + Phone No` already exists.
