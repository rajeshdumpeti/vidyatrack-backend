# VidyaTrack Backend Feature Walkthrough

## Purpose
This document explains the backend by feature area so a developer can quickly map product surfaces to backend ownership.

## Platform
Feature router: `app/features/platform/api.py`

Includes:
- health endpoints
- notification outbox trigger endpoint
- school onboarding phase 1
- CMS passthrough

Primary files:
- routes: `health.py`, `notifications.py`, `school_onboarding.py`, `cms.py`
- services: `school_onboarding.py`, `strapi.py`
- repositories: `school_onboarding.py`

Why it matters:
- this area contains operational and platform bootstrap flows
- onboarding is multi-entity and idempotent

## Auth
Feature router: `app/features/auth/api.py`

Includes:
- OTP request
- OTP verify
- auth debug helper
- `/auth/me`

Primary files:
- route: `auth.py`
- controller: `auth.py`
- service: `auth.py`
- repository: `auth.py`

High-risk behavior:
- rate limiting
- delivery fallback
- OTP hashing
- token generation

## Schools
Feature router: `app/features/schools/api.py`

Includes:
- school list
- school create
- school dashboard
- management dashboard
- principal dashboard

Primary files:
- routes: `schools.py`, `management_dashboard.py`, `principal_dashboard.py`
- services: `schools.py`, `dashboard.py`
- repositories: `schools.py`, `dashboard.py`

Key behavior:
- school-level counts
- dashboard aggregations
- super-admin guarded school admin views

## Students
Feature router: `app/features/students/api.py`

Includes:
- student list and create paths
- student import preview and commit
- student detail helper flows
- student notes

Primary files:
- routes: `students.py`, `student_notes.py`
- services: `students.py`, `student_notes.py`
- repositories: `students.py`

High-risk behavior:
- CSV import
- duplicate detection
- public ID generation
- student report-card/profile aggregation

## Academic
Feature router: `app/features/academic/api.py`

Includes:
- classes
- sections
- subjects
- attendance
- marks
- teaching assignments
- academic setup

Primary files:
- routes: `classes.py`, `sections.py`, `subjects.py`, `attendance.py`, `marks.py`, `teaching_assignments.py`, `academic_setup.py`
- services: matching domain services under `app/services`
- repositories: matching query helpers under `app/db/repositories`

High-risk behavior:
- attendance submission
- marks correction lock window
- notification outbox population
- school/section/subject joins

## Staffing
Feature router: `app/features/staffing/api.py`

Includes:
- teacher CRUD and teacher self-service
- management teachers
- management principal and onboarding

Primary files:
- routes: `teachers.py`, `teacher_me.py`, `teachers_me.py`, `management_teachers.py`, `management_principal.py`
- services: corresponding staffing services
- repositories: teachers and teacher surfaces where applicable

High-risk behavior:
- management principal OTP onboarding
- school ownership and role mapping

## Communications
Feature router: `app/features/communications/api.py`

Includes:
- communication history and send flows

Primary files:
- route: `communications.py`
- controller: `communications.py`
- service: `communications.py`

## How To Use This Walkthrough
When assigned a task:
1. identify the owning feature group
2. find the route module
3. follow the flow down into service and repository layers
4. check the existing test file before changing logic
