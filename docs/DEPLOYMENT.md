# Deployment and operations

## Local development and assessment

```bash
bash scripts/setup.sh --demo
bash scripts/start.sh
```

Default service: loopback port 8000, two Gunicorn workers. Health: `curl -fsS http://127.0.0.1:8000/health`. The application uses the existing checkout; no worktree is needed. No external service, secret or API key is required for local evaluation.

For Flask's development server instead of Gunicorn:

```bash
.venv/bin/flask --app looplocal run --host 127.0.0.1 --port 8000
```

Debug mode is not enabled by the saved scripts. Do not enable Flask debugging on a shared service.

## Private installation without public demo users

On a **fresh application directory/database**:

```bash
bash scripts/setup.sh
.venv/bin/flask --app looplocal create-admin
bash scripts/start.sh
```

The CLI prompts for administrator name, email and a hidden password, with confirmation. Do not provide secrets in command history or Git. Register actual members through the normal flow. Empty catalogue/clinic states work; administrators populate them in the UI.

Do not convert the supplied public demo database into a live service by changing only one password: every seeded account has a publicly known password. Start with a fresh, non-demo database and create real accounts. Preserve any needed real records via a planned data migration; never delete user data blindly.

## Runtime configuration

| Setting | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Optional externally managed Flask signing key | Random 0600 `instance/session.key` generated once |
| `COOKIE_SECURE=1` | Send session cookies only over HTTPS | Off for local HTTP testing |
| `BIND` | Bind address for `scripts/start.sh` | `127.0.0.1:8000` |
| `WORKERS` | Gunicorn workers | `2` |
| `BASE_URL` | Browser smoke target only | `http://127.0.0.1:8000` |
| `CHROMIUM_PATH` | Optional existing browser executable for smoke tests | System Chromium, else Playwright-managed Chromium |

`SECRET_KEY` should be managed by the deployment's secure runtime mechanism if used. Do not put real secret values in `.env` files committed to Git. The generated local key is sufficient for local use; do not replace it on every restart or existing sessions become invalid. Keep private file permissions on the instance directory and database. Setting `COOKIE_SECURE=1` while using plain HTTP prevents login cookies from working.

## Shared hosting

Use a Linux host with persistent storage and a reverse proxy that terminates TLS, limits request rate and only forwards to Gunicorn on loopback. Set `COOKIE_SECURE=1`. Run as a non-root service account. Configure restart-on-failure and log retention in your host's service manager. No specific external hosting provider was provisioned or validated by this project.

SQLite requires the **same persistent local disk** for all workers. Do not place it on ephemeral serverless storage or an unreliable network filesystem. Do not run independent containers with separate database copies and expect shared state. Increase deployment scope only after migrating the data layer and load testing.

Use application health checks plus an authenticated smoke test; an open port alone is not readiness. The included cloud check exercised Gunicorn with two workers and browser requests. It did not validate a public TLS domain.

## Backup and restoration

The SQLite database, WAL state and signing key are runtime state, ignored by Git. Use SQLite's online backup API rather than copying a live DB without its WAL:

```bash
mkdir -p /path/to/private-backups
.venv/bin/python - <<'PY'
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
folder = Path('/path/to/private-backups')
name = datetime.now(timezone.utc).strftime('looplocal-%Y%m%dT%H%M%SZ.sqlite')
with sqlite3.connect('instance/looplocal.sqlite') as source:
    with sqlite3.connect(folder / name) as target:
        source.backup(target)
PY
```

Use a restricted, encrypted backup location and an appropriate retention policy. Back up `instance/session.key` separately if preserving sessions is required. A new secret invalidates old cookies but does not lose accounts.

To restore, stop the service, preserve the current instance separately, install a verified backup as `instance/looplocal.sqlite`, ensure no stale `-wal`/`-shm` sidecars accompany the replacement, restore correct file ownership/permissions and restart. Check `PRAGMA integrity_check`, health and a representative login. Perform a restoration drill before relying on production backups. This deployment guide is procedural guidance; a full disaster-recovery drill was not executed in the cloud session.

## Maintenance

- `init-db` is additive/idempotent for the current schema; it is not a general migration system. Future schema changes require explicit migrations.
- Never use `seed-demo` in an existing real database. The command refuses nonempty databases unless the known demo admin is present, in which case it does nothing.
- Update pinned dependencies deliberately, review changes and rerun tests. Runtime requirements are in `requirements.txt`; exact tested runtime+test versions are in `requirements.lock`.
- Review audit records, overdue loans and inactive accounts. Resolve active repairs and loans before disabling members.
- In-app notifications are persistent but not push notifications or email. People must sign in to read them.
- Password recovery, account erasure, retention, verified volunteer credentials and multi-hub governance need a separate product policy and implementation before wider public operation.
