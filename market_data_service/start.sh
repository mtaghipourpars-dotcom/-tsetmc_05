#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
docker compose up -d --build
printf '%s\n' 'Open http://localhost:8000/docs'
