#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TLS_DIR="$ROOT_DIR/configs/tls/runtime"

python3 "$ROOT_DIR/scripts/doctor_runtime.py" --json || true

if [[ ! -d "$TLS_DIR" || -z "$(find "$TLS_DIR" -maxdepth 1 -type f \( -name '*.crt' -o -name '*.key' -o -name '*.pem' \) -print -quit 2>/dev/null)" ]]; then
  echo "[bootstrap] no TLS material detected; generating development certificate"
  bash "$ROOT_DIR/scripts/generate_dev_tls_cert.sh"
fi

echo "[bootstrap] running strict doctor"
python3 "$ROOT_DIR/scripts/doctor_runtime.py" --strict --json

echo "[bootstrap] starting vendored xCore runtime"
exec bash "$ROOT_DIR/scripts/start_real.sh"
