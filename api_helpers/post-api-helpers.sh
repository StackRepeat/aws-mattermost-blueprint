#!/usr/bin/env bash
set -euo pipefail

case "${WORKLOAD_ACTION:-create}" in
  destroy) exit 0 ;;
  create|update) ;;
  *) echo "Unsupported WORKLOAD_ACTION" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENDPOINT="$(terraform -chdir="$ROOT/terraform" output -raw endpoint)"
python3 "$ROOT/api_helpers/python/wait_ready.py" "$ENDPOINT"
