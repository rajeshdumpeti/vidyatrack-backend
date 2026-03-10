# VidyaTrack Backend Architecture

## Document Control
- Product: `VidyaTrack Backend`
- Audience: Backend engineers, full-stack engineers, engineering managers, QA, SRE, and onboarding developers
- Scope: Service architecture, API composition, feature boundaries, persistence layer, extension rules, and operational conventions
- Source of truth: Current repository implementation under `app/` and validated regression coverage under `tests/`

## Executive Summary
VidyaTrack backend is a FastAPI application backed by SQLAlchemy models, Alembic migrations, PostgreSQL-oriented schema design, and feature-oriented API composition.

The codebase is structured to preserve behavior while keeping responsibilities separate:
- `routes` own HTTP transport and dependency wiring
- `controllers` own request orchestration boundaries
- `services` own business flows
- `repositories` own query and persistence access
- `schemas` define request and response contracts
- `features` group product surfaces at API composition level

The architecture goal is predictable change under strict API stability constraints.

## Technology Stack
### Core
- Python `3.13` in local execution, designed for Python `3.12+`
- FastAPI
- SQLAlchemy ORM
- Alembic
- PostgreSQL-oriented schema design
- Uvicorn
- Pytest

### Supporting Infrastructure
- Pydantic v2
- CORS middleware
- application logging middleware
- email integration via Brevo
- WhatsApp integration client

## Runtime Entry Point
Application boot starts in `app/main.py`.

Startup sequence:
- logging is configured
- FastAPI app is instantiated
- CORS middleware is attached
- request logging middleware is attached
- versioned API router is mounted at `/api/v1`

This file should remain minimal. Product behavior belongs below the API layer, not in application bootstrap.

## Top-Level Structure
### `app/main.py`
Application assembly and middleware.

### `app/api/v1`
Versioned HTTP API surface.

Subfolders:
- `routes/`: thin FastAPI route modules
- `controllers/`: route-facing orchestration layer
- `schemas/`: request and response contracts
- `router.py`: API composition through feature routers

### `app/features`
Feature-oriented API grouping used for top-level router composition.

Current feature groups:
- `platform`
- `auth`
- `schools`
- `students`
- `academic`
- `staffing`
- `communications`

### `app/services`
Business orchestration and domain workflows.

Examples:
- OTP issuance and verification
- student import preview and commit
- school onboarding
- marks and attendance workflows
- dashboard aggregation

### `app/db/models`
SQLAlchemy model definitions representing persisted entities.

Examples:
- `School`
- `User`
- `Student`
- `Teacher`
- `Class`
- `Section`
- `Subject`
- `MarksRecord`
- `MarksSubmission`
- `OtpRequest`
- `NotificationOutbox`

### `app/db/repositories`
Persistence access layer for reusable query paths.

Repositories currently exist for high-churn areas like:
- auth
- dashboard
- marks
- school onboarding
- schools
- sections
- students
- subjects
- teacher surfaces
- teaching assignments

### `app/core`
Cross-cutting concerns and shared primitives.

Examples:
- config
- logging
- phone normalization
- role normalization
- UUID generation

### `app/integrations`
External provider clients and delivery adapters.

### `app/workers`
Async or batch-style background processing logic such as outbox processing.

## API Composition Model
The public API is mounted through `app/api/v1/router.py`, which now composes feature routers rather than listing every route module directly.

This gives two benefits:
- top-level API ownership is readable by product domain
- future file relocation under feature packages becomes safer

### Current feature router mapping
- `platform`: health, notifications, school onboarding, CMS
- `auth`: OTP auth surfaces
- `schools`: school admin and dashboard surfaces
- `students`: student CRUD and notes
- `academic`: classes, sections, subjects, attendance, marks, teaching assignments, academic setup
- `staffing`: teachers, teacher self-service, management staffing, management principal
- `communications`: messaging and timeline flows

## Layering Rules
### Route layer
Allowed:
- dependency injection
- response models
- path/query/body wiring
- HTTP-specific status code mapping already preserved by controllers/services

Not allowed:
- direct ORM queries
- direct transaction control
- inline Pydantic model declarations
- business rules

### Controller layer
Allowed:
- request-to-service adaptation
- transport-safe orchestration
- permission gate helpers where route reuse demands it

Not allowed:
- large query blocks
- persistence-heavy logic

### Service layer
Allowed:
- business workflows
- multi-step validation
- transaction boundaries
- entity creation and update orchestration
- provider fallbacks and side-effect sequencing

### Repository layer
Allowed:
- reusable ORM queries
- narrow persistence helpers
- data access helpers shared by multiple flows

Not allowed:
- HTTP exceptions for transport concerns unless they are already part of preserved behavior

## Schema Strategy
Pydantic models are centralized under `app/api/v1/schemas`.

This gives:
- a stable contract layer
- easier route review
- less duplication
- lower risk during refactors

Patterns in use:
- request input schemas
- response output schemas
- `ConfigDict(from_attributes=True)` for ORM-backed responses where needed
- field validators for normalized inputs such as phone, email, and school onboarding payloads

## Persistence Strategy
The ORM layer is centered on SQLAlchemy models under `app/db/models`.

Key patterns:
- strong foreign keys
- explicit public IDs for user-facing references
- internal UUID-based identifiers where required
- `server_default=func.now()` for persisted timestamp creation where appropriate
- public ID generation through `app/services/public_id.py` and `public_id_counters`

### Public ID model
Public IDs are part of the application contract for many entities.

Examples:
- schools
- classes
- sections
- subjects
- students
- teachers
- principals
- management admins

This means:
- tests must seed `public_id` where the model requires it
- feature flows creating those entities must pass through the public ID service path

## Authentication and Authorization
The backend currently uses OTP-based authentication with JWT-style token issuance behavior implemented in the auth service flow.

Relevant layers:
- route: `app/api/v1/routes/auth.py`
- controller: `app/api/v1/controllers/auth.py`
- service: `app/services/auth.py`
- repository: `app/db/repositories/auth.py`

Authorization patterns:
- dependency-based current user resolution
- role guards such as management and super admin requirements
- school-context validation where endpoints are school scoped

## Multi-Tenancy Model
VidyaTrack is school-scoped across large parts of the API.

This means:
- many endpoints require `school_id`
- role access must be interpreted together with school mappings
- query scopes must not leak across schools
- tests should assert school-scoped isolation where relevant

## Integrations and Side Effects
The backend integrates with external delivery systems for OTP and communication-style workflows.

Current examples:
- Brevo email
- WhatsApp template delivery

Side-effect protection patterns:
- fallback ordering in auth OTP delivery
- notification outbox records for marks and attendance submission
- idempotency keys for school onboarding

## Testing Strategy
The repository now has focused regression coverage for the highest-risk refactor zones.

Covered areas include:
- auth OTP request behavior
- academic setup
- student import
- platform school dashboard
- school onboarding phase 1
- marks
- schools

The preferred regression style is:
- thin in-memory SQLite setup
- dependency overrides for FastAPI
- route-level assertions against real service code paths

## Extension Guidelines
When adding a new backend feature:
1. decide the owning feature package
2. define request and response schemas first
3. add a thin route
4. add or extend a controller
5. place business logic in a service
6. extract reusable queries into a repository when appropriate
7. add regression tests at route level

## Non-Goals
This architecture does not currently enforce:
- strict physical co-location of every route/controller/schema/service file under each feature package
- full mypy gate enforcement in CI
- async database access

Those can be phase-3 improvements if desired, but the current system is already structured to support them.
