# VidyaTrack Backend Production Readiness Checklist

## 1. Document Purpose
This checklist is the formal release gate for promoting the VidyaTrack backend to production.

It is intended for:
- backend engineering
- QA
- platform engineering
- release management
- engineering leadership

## 2. Release Metadata
- Release name:
- Release version:
- Release branch:
- Commit SHA:
- Artifact reference:
- Environment under review:
- Release owner:
- QA owner:
- Engineering approver:
- Proposed production date:
- Rollback owner:

## 3. Scope Confirmation
### Mandatory
- release scope is documented and frozen
- in-scope fixes and features are listed
- out-of-scope items are listed
- known issues are documented
- final release SHA is recorded
- no unreviewed late changes exist after QA signoff

## 4. Repository and Build Health
### Mandatory
- repository compiles successfully
- no unresolved merge conflicts exist
- no debug-only code paths are shipping unintentionally
- migrations are not modified unexpectedly
- dependency changes are reviewed
- no abandoned refactor folders remain

### Validation
- `python -m compileall app`
- targeted regression suites attached

## 5. Configuration Readiness
### Mandatory
- required environment variables are defined
- JWT secret is set correctly
- OTP delivery mode is correct for production
- email integration config is correct
- WhatsApp integration config is correct
- database connection config is correct
- CORS origins are correct
- no development-only host assumptions remain

## 6. Database and Migration Safety
### Mandatory
- Alembic head is correct
- pending migrations are reviewed
- backward compatibility of schema changes is understood
- no migration was edited after being applied in shared environments
- public ID generation paths are valid for new entities

## 7. Authentication and Authorization
### Mandatory
- OTP request works
- OTP verify works
- invalid OTP path works
- rate limiting works
- `/auth/me` works for valid token context
- unauthorized access is denied
- role-guarded routes are enforced
- school-scoped access is enforced

## 8. Core Workflow Readiness
### Mandatory
- school onboarding phase 1 works
- school dashboard endpoints work
- student import preview and commit work
- marks record and submit work
- academic setup endpoints work
- communications endpoints work in the intended environment
- management principal onboarding flow works

## 9. Data Integrity
### Mandatory
- create/update flows persist the intended entities only
- transaction rollback occurs on conflict paths
- idempotency behaves correctly where supported
- public IDs are generated for required entities
- no cross-school data leakage is observed

## 10. Observability
### Mandatory
- request logging middleware is active
- status code and latency fields are present in request logs
- provider failures are observable in logs
- operational owners know where runtime logs are collected

## 11. Failure Handling
### Mandatory
- 400 / 401 / 403 / 404 / 409 / 422 / 429 / 503 paths are understood for changed areas
- external provider failures do not crash the service
- error detail payloads are stable for existing clients

## 12. Release Gate
Release should not proceed unless:
- compile passes
- targeted regressions pass
- configuration is verified
- QA signoff is recorded
- rollback path is clear
