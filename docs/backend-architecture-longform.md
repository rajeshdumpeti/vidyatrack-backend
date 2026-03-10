# VidyaTrack Backend Architecture Longform

## 1. Purpose
This document explains how the VidyaTrack backend is organized at a level suitable for senior engineers, leads, and maintainers making structural decisions.

Use this document when you need to understand:
- where business logic should live
- why the current layering exists
- how API stability was preserved during refactor work
- how to extend the backend without regressing behavior

## 2. Architectural Principles
The backend was refactored under one non-negotiable constraint: the API had to behave exactly the same.

That led to a practical architecture:
- transport concerns are isolated
- behavior is extracted instead of rewritten
- query logic is gradually isolated behind repositories
- feature ownership becomes visible at API composition boundaries

The design values are:
- behavior preservation
- readability
- testability
- lower merge-conflict risk
- explicit ownership

## 3. Mental Model
Think about the backend in this order:
1. FastAPI receives the request
2. route resolves dependencies and request models
3. controller adapts request inputs into application calls
4. service executes business flow
5. repository performs reusable data access
6. ORM models persist and load entities
7. schemas shape responses back to the route

If you keep that sequence in mind, most files become straightforward.

## 4. Why Feature Routers Were Added
The repo originally had one flat API router importing many route modules directly.

That worked, but it made ownership harder to see at a glance.

The current `app/features/*/api.py` layer solves that by grouping top-level surfaces into business areas:
- platform
- auth
- schools
- students
- academic
- staffing
- communications

This is an intentionally safe intermediate step between:
- a flat route registry
- and a fully co-located feature filesystem

It improves readability without forcing risky mass file movement.

## 5. Why Routes Must Stay Thin
Route files are the least stable place to keep domain logic because:
- they mix HTTP concerns with business behavior
- they become hard to test in isolation
- they encourage direct DB usage
- they grow into god files quickly

In this repo, the route layer should answer only:
- what path is this?
- what inputs does it accept?
- what dependencies does it require?
- which application function does it call?

Everything else belongs elsewhere.

## 6. Why Controllers Exist
Some teams skip controllers and route directly into services.

That can work on smaller apps, but controllers are useful here because:
- FastAPI dependency and transport decisions stay out of services
- controllers act as an application seam when multiple routes share orchestration
- tests and future tracing hooks have a stable entry point between transport and business logic

Controllers in this codebase should stay small.

## 7. Why Services Own Business Logic
Services are where domain behavior should be obvious.

Examples in this repo:
- auth OTP issuance and fallback delivery
- student CSV preview and commit
- school onboarding phase 1
- marks record and submission flows
- management principal onboarding

A service is the correct place when logic:
- spans multiple entities
- has multiple validation branches
- opens or depends on transaction ordering
- performs side effects
- coordinates repository calls

## 8. Repository Boundaries
Repositories exist to isolate reusable query logic, not to mimic every ORM call one-for-one.

Good repository candidates:
- repeated `get-by-scope` lookups
- list queries used in multiple flows
- scoped joins
- reusable count or existence checks

Bad repository candidates:
- one-off lines that make the service harder to read
- artificial wrappers around every `db.add`
- generic base repositories that hide behavior

This repo uses repositories pragmatically, not dogmatically.

## 9. Public ID and Tenant Code Design
Public IDs are part of the product contract.

That is important.

They are not cosmetic fields. They affect:
- user-facing references
- test setup
- onboarding flows
- entity creation paths

The `public_id` service logic also owns tenant-code derivation and counter sequencing.

This is why some test fixtures needed repair after the schema matured.

## 10. High-Risk Domains
Some backend areas are structurally more sensitive than others.

### Auth
Risk factors:
- provider fallback behavior
- OTP throttling
- token issuance
- monkeypatch-heavy tests

### Student Import
Risk factors:
- CSV parsing
- duplicate detection
- commit token lifecycle
- public ID generation
- date normalization

### School Onboarding
Risk factors:
- idempotency
- multi-entity creation
- permission enforcement
- feature and contact sub-record persistence

### Marks and Attendance
Risk factors:
- correction windows
- submission locking
- notification outbox side effects
- school/section/subject joins

These domains deserve route-level regression coverage before structural changes.

## 11. Current Safe Evolution Path
The repo is now in a good state for controlled evolution.

The recommended sequence for future architecture work is:
1. keep adding tests before moving files
2. physically co-locate modules under `app/features/<domain>/...`
3. leave compatibility imports only where external tests or tools still reference old paths
4. gradually shrink legacy flat folders
5. only then consider stronger static enforcement such as import boundaries or mypy gates

## 12. Why This Is “Industrial” Enough
Industrial-grade architecture is not just deep folder nesting.

What matters is:
- stable dependency direction
- predictable ownership
- testability
- operational clarity
- ease of safe change

The backend now has those properties:
- thin transport layer
- centralized schemas
- service-owned business flows
- repository-backed reusable data access
- feature-level API composition
- route-level regression coverage for critical domains

That is the right standard for an actively evolving product backend.
