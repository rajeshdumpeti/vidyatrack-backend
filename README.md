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

yaml
Copy code

---

## Prerequisites

Ensure the following are installed on your system:

- Python **3.12+**
- Git

Verify:

```bash
python3 --version
git --version
How to Run the Backend (Step-by-Step, No Assumptions)
1. Clone the Repository
bash
Copy code
git clone https://github.com/rajeshdumpeti/vidyatrack-backend.git
cd vidyatrack-backend
2. Create and Activate Virtual Environment
Important: Never run the backend without a virtual environment.

bash
Copy code
python3 -m venv .venv
source .venv/bin/activate
Verify activation:

bash
Copy code
which python
Expected output:

bash
Copy code
.../vidyatrack-backend/.venv/bin/python
If this is wrong → STOP. Fix the virtual environment before continuing.

3. Install Dependencies
bash
Copy code
pip install -r requirements.txt
Verify FastAPI installation:

bash
Copy code
python -c "import fastapi; print(fastapi.__version__)"
4. Run the Backend Server
bash
Copy code
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Expected output:

nginx
Copy code
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
5. Verify Health Endpoints
Liveness
bash
Copy code
curl http://127.0.0.1:8000/api/v1/health/live
Readiness
bash
Copy code
curl http://127.0.0.1:8000/api/v1/health/ready
Expected response:

json
Copy code
{ "status": "ok" }
If these fail → the backend is not healthy.

🧪 Postman Usage (Local Development)
Collection
Name: vidyatrack-backend

Environment
Name: vidyatrack-local

Variable	Value
base_url	http://127.0.0.1:8000

Requests
text
Copy code
GET {{base_url}}/api/v1/health/live
GET {{base_url}}/api/v1/health/ready
🧯 Troubleshooting Guide (Read This Before Panicking)
❌ ModuleNotFoundError: No module named app
Cause:
Running uvicorn from the wrong directory.

Fix:

bash
Copy code
cd vidyatrack-backend
uvicorn app.main:app --reload
❌ Address already in use
Cause:
Port 8000 is already occupied.

Fix:

bash
Copy code
lsof -i :8000
kill -9 <PID>
OR run on another port:

bash
Copy code
uvicorn app.main:app --port 8001
❌ command not found: uvicorn
Cause:
Virtual environment not activated.

Fix:

bash
Copy code
source .venv/bin/activate
pip install -r requirements.txt
❌ Health endpoint returns 404
Cause:
Wrong URL or missing /api/v1.

Correct URLs:

bash
Copy code
/api/v1/health/live
/api/v1/health/ready
❌ Code changes not reflecting
Cause:
Server not started with --reload.

Fix:

bash
Copy code
uvicorn app.main:app --reload
🔄 Git Workflow (Expected)
Default branch: main

Commit conventions
feat: → new functionality

docs: → documentation

chore: → setup / tooling

Do NOT commit
.venv/

.env

local cache files

🧱 Architectural Notes (Why Things Are This Way)
Versioned APIs (/api/v1)
Prevents breaking clients when APIs evolve.

Routes separated by domain
Avoids god-files and keeps ownership clear.

Health endpoints split (live vs ready)
Required for real deployments (Docker, Kubernetes, ECS).

🚦 Current Scope vs Future Scope
Implemented
Health checks

API versioning

Clean project structure

Planned
Configuration management (core/config.py)

Logging middleware

SQLAlchemy + Alembic

Authentication & RBAC

Domain modules (schools, users, attendance)

📌 Operational Rule (Important)
If health endpoints are green, the backend is considered:

runnable

deployable

safe to extend

If health endpoints fail → do not proceed with feature work.

yaml
Copy code

---

### Mentor verdict (straight talk)

This README is **not beginner junk**.
It’s something a **senior engineer or DevOps person can actually operate from**.

If you want, next we can:
- add **CONTRIBUTING.md**
- add **release versioning (`v0.1.0`)**
- or move into **config + logging foundation**

You decide the next step.
```

<!-- Precees to create API for this project -->

Create file in modals first and schema
import in modals/**init**.py
then run -- below two lines
alembic revision --autogenerate -m "create classes and sections tables"
alembic upgrade head
which creates file in alembic/versions example: d424429bc79d_create_classes_and_sections_tables.py
Then create new file example : app/api/v1/routes/classes.py
then add from app.api.v1.routes import classes in app/api/v1/router.py and include api_router.include_router(classes.router) in same file
test create api's in postman
