# VidyaTrack Backend QA Test Plan

## 1. Purpose
This document defines the minimum backend QA scope for validating a release candidate of the VidyaTrack backend.

It is intended for:
- backend engineering
- QA
- release management
- engineering leadership

## 2. Validation Scope
This plan focuses on:
- API contract correctness
- role and school authorization behavior
- data integrity
- transaction correctness
- critical workflow regression

## 3. Test Layers
### Layer 1: Static validation
- repository compiles
- imports resolve
- app boots successfully

Baseline command:
```bash
python -m compileall app
```

### Layer 2: Focused regression suites
Run the high-signal route-level suites:
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

### Layer 3: Exploratory or integration validation
Manually validate highest-risk flows against a running app where needed.

## 4. Critical Workflow Coverage
### Auth
Validate:
- OTP request success
- OTP throttling
- WhatsApp failure with email fallback
- email-only path
- `/auth/me` behavior under valid token context

### School Onboarding
Validate:
- successful phase 1 school onboarding
- conflict detection
- idempotency key reuse behavior
- draft create, update, and get

### Schools
Validate:
- schools list
- teacher and student counts
- dashboard counts
- super-admin access enforcement
- create school

### Students
Validate:
- import preview
- invalid row reporting
- import commit
- created row counts

### Marks
Validate:
- marks record creation
- idempotent update behavior
- marks submit
- list by section and subject
- invalid section handling

### Academic Setup
Validate:
- classes, sections, and subjects returned for a valid school

## 5. Authorization Matrix
At minimum, verify:
- `SUPER_ADMIN`
- `MANAGEMENT`
- `PRINCIPAL`
- `TEACHER`

For each major protected area confirm:
- allowed role succeeds
- disallowed role returns the expected auth failure

## 6. Data Integrity Checks
QA should explicitly watch for:
- school-scoped isolation
- duplicate prevention
- idempotent replay correctness
- correct transaction rollback on conflict
- consistent response models after create/update

## 7. Regression Risk Areas
Prioritize extra review for:
- auth provider fallback logic
- school onboarding multi-entity creation
- student import token lifecycle
- public ID generation
- marks correction lock behavior
- notification outbox side effects

## 8. Exit Criteria
Backend release candidate can pass QA when:
- compile step passes
- focused regression suites pass
- no API contract regressions are found in changed areas
- no unexplained authorization regressions remain
- known issues are documented and accepted by owners
