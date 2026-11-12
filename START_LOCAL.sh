#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec python3 market_data_service/scripts/launch_local.py "$@"
