#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 scripts/setup_env.py
docker compose up -d --build
printf '%s\n' 'Open http://localhost:8000'
