#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Bind locally by default. Put a TLS reverse proxy in front of shared deployments.
exec .venv/bin/gunicorn 'looplocal:create_app()' --bind "${BIND:-127.0.0.1:8000}" --workers "${WORKERS:-2}" --timeout 30 --access-logfile -
