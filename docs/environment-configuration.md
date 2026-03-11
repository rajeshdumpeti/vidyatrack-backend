# Backend Environment Configuration

This backend now uses one codebase for all environments:

- `dev` branch -> development runtime -> Neon dev database
- `stage` branch -> staging runtime -> Neon stage database
- `main` branch -> production runtime -> Render PostgreSQL database

## Automatic environment selection

The selection logic lives in [app/core/config.py](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/app/core/config.py).

It resolves the active database in this order:

1. `DATABASE_URL`
2. `DATABASE_URL_DEV` when `APP_ENV=dev`
3. `DATABASE_URL_STAGE` when `APP_ENV=stage`
4. `DATABASE_URL_PROD` when `APP_ENV=prod`
5. Local `DB_*` fallback only for `dev` and `test`

That means the same startup command works everywhere:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Only the environment variables change.

## File-by-file notes

### [app/core/config.py](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/app/core/config.py)

Use:

```bash
APP_ENV=dev DATABASE_URL_DEV='postgresql+psycopg://...' uvicorn app.main:app --reload
APP_ENV=stage DATABASE_URL_STAGE='postgresql+psycopg://...' uvicorn app.main:app --reload
APP_ENV=prod DATABASE_URL_PROD='postgresql+psycopg://...' uvicorn app.main:app --reload
```

Test:

```bash
APP_ENV=test JWT_SECRET=test OTP_PEPPER=test pytest -q
```

Security:

- Stage and prod fail fast if `JWT_SECRET` or `OTP_PEPPER` still use insecure defaults.
- Secrets are read from environment variables only; none are embedded in application code.

### [app/db/session.py](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/app/db/session.py)

Use:

- Import `SessionLocal` and `engine` exactly as before.
- Pool sizing changes automatically by `APP_ENV`.

Test:

```bash
APP_ENV=dev DATABASE_URL_DEV='postgresql+psycopg://...' python -c "from app.db.session import engine; print(engine.url)"
```

Security:

- `pool_pre_ping` reduces stale-connection errors that can leak into request failures.
- Pool sizes stay intentionally small in lower environments to avoid exhausting free/shared database limits.

### [alembic/env.py](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/alembic/env.py)

Use:

```bash
APP_ENV=dev DATABASE_URL_DEV='postgresql+psycopg://...' alembic upgrade head
APP_ENV=stage DATABASE_URL_STAGE='postgresql+psycopg://...' alembic upgrade head
APP_ENV=prod DATABASE_URL_PROD='postgresql+psycopg://...' alembic upgrade head
```

Test:

```bash
APP_ENV=stage DATABASE_URL_STAGE='postgresql+psycopg://...' alembic current
```

Security:

- Alembic now uses the same resolved URL as the app, which removes configuration drift.
- Production migrations should run from CI or a controlled operator shell, not from a developer laptop with ad hoc secrets.

### [render.yaml](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/render.yaml)

Use:

- Import the blueprint into Render.
- Add the real secrets in each service after creation.
- Keep `autoDeployTrigger: off` so GitHub Actions controls migration-first deploys.

Test:

- Push to `dev`, `stage`, or `main` and verify the matching Render service is the only one deployed.

Security:

- Sensitive values are marked `sync: false`, so the blueprint never stores live secrets in git.
- Production is assigned a paid plan because free services are not appropriate for a live API.

### [.github/workflows/ci.yml](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/.github/workflows/ci.yml)

Use:

- Create GitHub Environments: `development`, `staging`, `production`
- In each environment, add:
  - `DATABASE_URL`
  - `JWT_SECRET`
  - `OTP_PEPPER`
  - `RENDER_DEPLOY_HOOK_URL`

Test:

- Open a PR into `dev`, `stage`, or `main` and confirm the `test` job runs.
- Push to one of those branches and confirm migrations run before the Render deploy hook fires.

Security:

- GitHub Environment secrets keep database credentials and deploy hooks out of the repository.
- Environment protection rules can require approvals for `production`.

### [.env.dev.example](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/.env.dev.example), [.env.stage.example](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/.env.stage.example), [.env.prod.example](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/.env.prod.example), [.env.example](/Users/rajeshdumpeti/Documents/vidyatrack/vidyatrack-backend/.env.example)

Use:

```bash
cp .env.dev.example .env
cp .env.stage.example .env
cp .env.prod.example .env
```

Test:

```bash
APP_ENV=dev python -c "from app.core.config import settings; print(settings.resolved_database_url)"
APP_ENV=stage python -c "from app.core.config import settings; print(settings.resolved_database_url)"
APP_ENV=prod python -c "from app.core.config import settings; print(settings.resolved_database_url)"
```

Security:

- Only example templates are committed.
- Real `.env`, `.env.dev`, `.env.stage`, `.env.prod`, and `.env.local` files are ignored by git.

## Recommended branch-to-environment contract

- `dev` branch deploys only to the Render dev service with `APP_ENV=dev`
- `stage` branch deploys only to the Render stage service with `APP_ENV=stage`
- `main` branch deploys only to the Render prod service with `APP_ENV=prod`

As long as that contract is preserved, the backend does not need any environment-specific code changes.
