# Reusable cloud setup instructions

Use the existing checkout at `/workspace/FYP2`. Every cloud task already has an isolated environment; **do not create a Git worktree unless the user explicitly asks**.

## Install / refresh

```bash
cd /workspace/FYP2
bash scripts/setup.sh --demo
.venv/bin/python -m pytest -q
```

Python 3.12 is the validated interpreter. Dependencies come from PyPI over normal verified HTTPS; no private package credentials or external services are required. Public GitHub repository access uses the platform-provided HTTPS Git authentication. Do not request or extract personal tokens merely because token variables are absent.

## Start after snapshot restoration

The virtual environment and initialized `instance/` directory are retained files. Processes do not survive environment snapshots. Check for an existing instance first:

```bash
curl -fsS http://127.0.0.1:8000/health
```

If not running, from the checkout run `bash scripts/start.sh` in a long-lived process session. Default is local port 8000 with two Gunicorn workers. Readiness requires a successful health response **and** an authenticated dashboard request / browser workflow. Do not present localhost preview links as user-facing onboarding previews.

Optional browser verification:

```bash
.venv/bin/python -m pip install -r requirements-browser.txt
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/browser_smoke.py
```

Use the installed system Chromium when browser download hosts are restricted. Browser smoke creates a demo repair and refreshes screenshots; use only a local demo database. Use `docs/DEPLOYMENT.md` for a non-demo installation.

## Configuration persistence status

These instructions and scripts are saved in the repository. During this setup session, the environment configuration draft read failed twice with `INVALID_ARGUMENT` (“current environment draft could not be verified”). A subsequent save of `install_script` and `start_skill` also returned `INVALID_ARGUMENT` and **did not confirm persistence**. No network settings, repositories or secret bindings were replaced. The current machine was installed and validated independently.

Consequently, repository-based setup is reproducible, but cloud configuration draft persistence and publication are not claimed. When environment settings are available, use the install/start instructions above as the reusable fields and publish through the product. Do not treat this document as evidence a published environment snapshot exists.
