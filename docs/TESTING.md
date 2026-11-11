# Validation evidence

Validated locally on **11 November 2026 (Malaysia time)** using Python **3.12.14**, Flask **3.1.2**, SQLite, Gunicorn **23.0.0** (two workers) and the cloud's system Chromium through Playwright **1.56.0**.

## Executed results

| Check | Result |
|---|---|
| Initial dependency installation | Passed, TLS verification retained |
| Repeat `bash scripts/setup.sh --demo` | Passed, existing database/seed records preserved |
| `.venv/bin/python -m pytest -q` | **30 passed**; no failures or skipped tests |
| `.venv/bin/python -m pip check` | No broken requirements |
| `.venv/bin/python -m compileall -q looplocal` | Passed |
| Gunicorn startup and `/health` | Passed; status `ok` |
| Stop/restart Gunicorn using saved `scripts/start.sh` | Passed; database records retained; subsequent browser login and workflow succeeded |
| Browser desktop/mobile navigation | Passed at 1440px desktop and 390px mobile; tested main authenticated pages for horizontal overflow |
| Browser full repair workflow | Passed: resident creates item → volunteer claims → in progress → repaired → public passport |
| Browser JavaScript errors | None observed during the smoke run |
| SQLite `PRAGMA integrity_check` | `ok` |
| SQLite `PRAGMA foreign_key_check` | Zero violations |

The browser smoke was rerun after the last application changes and service restart. Screenshots are current-run artifacts, not mockups. Browser runs add demo records, so later dashboard totals can differ from the original seed totals (3 completed items, 17.3 kg).

## Automated coverage

`tests/test_workflows.py` contains isolated functional tests, including parameterized role/date cases:

- Login/logout, invalid login feedback, registration and role escalation rejection.
- CSRF and security response headers.
- Core pages for all three roles and administrator-only export.
- Complete repair workflow, participant-only discussion and public passport privacy.
- Owner inability to fabricate completion; invalid transitions and insufficient completion notes.
- Hazard rejection, invalid categories, nonfinite and out-of-range weights.
- Volunteer skill checks and maximum active workload.
- Inclusive overlapping reservations, cancellation/return permissions, multiple-copy daily capacity and date bounds.
- Concurrent last-copy reservation: **one success, one capacity rejection**.
- Concurrent last-clinic-place registration: **one success, one capacity rejection**.
- Concurrent repair claims: **one assignment only**.
- Overdue custody blocks fresh reservations; existing bookings cannot check out a physically unavailable copy.
- Clinic registration duplicates, cancellation, notification and Malaysia-to-UTC conversion.
- Impact CSV totals, absence of identity fields and completed-only counting.
- Password change and HTML escaping.
- Account disabling, stale-session rejection and tool retirement.
- Login throttle, initialization/seed repeatability, public-passport availability and health/errors.

Fixtures create a fresh temporary database for every test. Concurrency tests use independent clients in threads against the same SQLite file, synchronized at a barrier. They are consistency checks, not a throughput/load benchmark.

## Reproduce

```bash
bash scripts/setup.sh --demo
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
bash scripts/start.sh
```

In another terminal, after installing `requirements-browser.txt`:

```bash
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/browser_smoke.py
```

If using a Playwright-managed browser, run `python -m playwright install chromium` first and omit `CHROMIUM_PATH` when no system Chromium is installed. Cloud browser downloads were denied by network policy; using the already installed `/usr/bin/chromium` resolved browser validation. The initial browser installation attempt also encountered an unwritable user-cache location; no browser download or cache modification is needed with the system browser.

Early smoke-script selector mismatches were corrected to account for decorative arrow text in button accessible names. Those were test-driver issues. The final workflow completed successfully. All reported pass results refer to final runs, not those initial attempts.

## Screenshots

- [Desktop overview](screenshots/dashboard-desktop.png)
- [Mobile overview](screenshots/dashboard-mobile.png)
- [Tool library](screenshots/tools-desktop.png)
- [Public item passport](screenshots/passport-desktop.png)

## Not executed / not claimed

- GitHub-hosted CI run: workflow is included; local checks are the recorded evidence.
- Public hosting, TLS domain provisioning, fresh published cloud-task restoration.
- Formal penetration test, full WCAG audit, load benchmark, real hardware safety testing.
- Field trials, SUS scores, stakeholder acceptance results or measured environmental impact.
- Full backup disaster-recovery drill.

The environment draft API returned `INVALID_ARGUMENT`; cloud draft persistence and publication remain unconfirmed, as recorded in [CLOUD_SETUP.md](CLOUD_SETUP.md). This is distinct from the successfully installed and running application in the current machine.
