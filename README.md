# vidyatrack-backend

Backend service for the **VidyaTrack** platform.

This repository contains the backend API built using **FastAPI**, following an enterprise-grade, modular, and versioned architecture.  
The backend is designed to be **upgrade-friendly**, **maintainable**, and **production-ready**, starting with health checks and expanding toward authentication, RBAC, and database-backed features.

---

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Dependency Management:** pip + requirements.txt
- **(Upcoming):**
  - SQLAlchemy (ORM)
  - Alembic (DB migrations)
  - PostgreSQL

---

## Project Structure

backend/
├── app/
│ ├── main.py # Application entry point
│ ├── api/
│ │ └── v1/ # Versioned API layer
│ │ ├── router.py
│ │ └── routes/
│ │ └── health.py # Health check endpoints
│ ├── core/ # Config, logging, security (upcoming)
│ └── db/ # Database, ORM, migrations (upcoming)
├── requirements.txt
├── README.md
├── .gitignore
└── .venv/ # Local virtual environment (not committed)

---

## Prerequisites

Ensure the following are installed on your system:

- Python **3.12+**
- Git

Verify:

```bash
python3 --version
git --version
```
