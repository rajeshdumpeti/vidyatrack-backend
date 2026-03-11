# VidyaTrack Backend Junior Developer Onboarding Guide

## 1. Why This Exists
This guide is for junior backend developers joining the VidyaTrack backend.

By the end of it, you should understand:
- how the API is assembled
- where to read a feature
- where to add new code
- how to avoid common mistakes

## 2. First Mental Model
Read the backend in this order:
1. route
2. controller
3. schema
4. service
5. repository
6. model
7. tests

That order will save you time.

## 3. Stack
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- Pytest

What each one does:
- FastAPI: HTTP API
- Pydantic: input and output validation
- SQLAlchemy: ORM and persistence
- Alembic: migrations
- Pytest: regression tests

## 4. Important Folders
### `app/main.py`
App startup, middleware, and router mounting.

### `app/api/v1/routes`
HTTP endpoints only.

### `app/api/v1/controllers`
Thin orchestration layer between routes and services.

### `app/api/v1/schemas`
Pydantic request and response models.

### `app/services`
Business logic.

### `app/db/repositories`
Reusable database access.

### `app/db/models`
Database entities.

### `app/features`
Top-level feature grouping for API composition.

### `tests`
Regression coverage.

## 5. How To Read a Feature
Use this sequence:
1. find the route file
2. inspect the request and response schemas
3. inspect the controller
4. inspect the service
5. inspect any repository calls
6. inspect the tests

Example:
- `app/api/v1/routes/marks.py`
- `app/api/v1/schemas/marks.py`
- `app/api/v1/controllers/marks.py`
- `app/services/marks.py`
- `app/db/repositories/marks.py`
- `tests/test_marks.py`

## 6. What Belongs Where
### Put code in routes when:
- it defines path, method, and response model
- it resolves FastAPI dependencies

### Put code in controllers when:
- a route needs a thin adaptation layer
- multiple route handlers share transport-facing orchestration

### Put code in schemas when:
- it validates request input
- it defines response output shape

### Put code in services when:
- it is real business logic
- it spans validation and persistence
- it creates or updates multiple entities
- it manages workflow ordering

### Put code in repositories when:
- the query is reused
- the query is large enough to distract from service logic
- the data access pattern is likely to be shared

### Put code in models when:
- it defines persisted database structure

## 7. Common Mistakes To Avoid
- do not put ORM queries directly in routes
- do not define new `BaseModel` classes inside routes
- do not hide business rules in helper functions with unclear names
- do not bypass public ID generation for entities that require it
- do not add new features without route-level tests
- do not change response shapes casually

## 8. School Context Matters
Many APIs are school scoped.

That means:
- you often need `school_id`
- role checks alone are not enough
- data must not leak across schools

When debugging, always ask:
- which school is this request for?
- how was the school resolved?
- does the current user actually have access?

## 9. Public ID Rules
Several models require `public_id`.

Examples:
- School
- Class
- Section
- Subject
- Student
- Teacher

If you create these in code or tests, remember:
- runtime creation should go through the public ID service path
- tests must provide required `public_id` values unless the flow generates them

## 10. How To Add a New Endpoint Safely
Checklist:
1. add request and response schemas
2. add a route with dependencies and response model
3. add a controller function
4. add or extend a service
5. add repository helpers if queries are reusable
6. add or update tests

## 11. How To Debug Failures
Use this order:
1. confirm route and params
2. confirm schema validation
3. inspect controller input handoff
4. inspect service branching
5. inspect repository query scope
6. inspect model constraints
7. inspect the test fixture data

Most common bugs in this repo come from:
- missing school context
- missing required `public_id`
- role mismatch
- naive vs aware datetime issues
- tests using incomplete fixture setup

## 12. Commands You Will Use Often
Run targeted tests:
```bash
pytest -q tests/test_marks.py
```

Run multiple critical suites:
```bash
DEBUG=false OTP_DELIVERY_MODE=provider pytest -q \
  tests/test_auth_otp_request.py \
  tests/test_academic_setup.py \
  tests/test_students_import.py \
  tests/test_platform_school_dashboard.py \
  tests/test_school_onboarding_phase1.py \
  tests/test_marks.py \
  tests/test_schools.py
```

Check imports and syntax:
```bash
python -m compileall app
```

## 13. Good Habits In This Repo
- keep route files short
- name service functions after business intent
- keep schemas explicit
- add tests when you touch behavior
- prefer extraction over rewrite
- keep error details stable unless you intentionally version the API
