# VidyaTrack Backend

Backend service for the VidyaTrack platform.

## Core Stack
- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL-oriented schema design
- Pytest

## Local Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health checks:
```bash
curl http://127.0.0.1:8000/api/v1/health/live
curl http://127.0.0.1:8000/api/v1/health/ready
```

## Project Structure
- `app/main.py`: application bootstrap
- `app/api/v1`: versioned API layer
- `app/features`: feature-level API composition
- `app/services`: business logic
- `app/db/models`: ORM entities
- `app/db/repositories`: reusable persistence access
- `app/core`: config, logging, roles, phone helpers, shared primitives
- `app/integrations`: external provider clients
- `app/workers`: background processing helpers
- `tests`: regression coverage

## Documentation
- [Backend Environment Configuration](./docs/environment-configuration.md)
- [Backend Architecture](./docs/backend-architecture.md)
- [Backend Architecture Longform](./docs/backend-architecture-longform.md)
- [Backend Junior Onboarding](./docs/backend-junior-onboarding.md)
- [Backend Feature Walkthrough](./docs/backend-feature-walkthrough.md)
- [Backend QA Test Plan](./docs/backend-qa-test-plan.md)
- [Backend Production Readiness Checklist](./docs/backend-production-readiness-checklist.md)
- [Backend Release Signoff](./docs/backend-release-signoff.md)

## High-Signal Verification
```bash
python -m compileall app
DEBUG=false OTP_DELIVERY_MODE=provider pytest -q \
  tests/test_auth_otp_request.py \
  tests/test_academic_setup.py \
  tests/test_students_import.py \
  tests/test_platform_school_dashboard.py \
  tests/test_school_onboarding_phase1.py \
  tests/test_marks.py \
  tests/test_schools.py
```
