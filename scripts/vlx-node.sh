#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
role=${VLX_ROLE:-rpc}
[[ "$role" == rpc || "$role" == validator ]] || { echo 'VLX_ROLE must be rpc or validator' >&2; exit 1; }
compose=(docker compose --project-directory "$ROOT" -f "$ROOT/docker-compose.yml" -f "$ROOT/deploy/compose.$role.yml")
if [[ "${VLX_MONITORING:-0}" == 1 ]]; then compose+=(-f "$ROOT/deploy/compose.monitoring.yml"); fi
cmd=${1:-help}; shift || true
case "$cmd" in
  init)
    [[ -e .env ]] || cp .env.example .env
    echo 'Review .env before start; existing .env was preserved.' ;;
  build|start|stop|logs|config)
    [[ -f .env ]] || { echo 'Run bash vlx-node.sh init first' >&2; exit 1; }
    case "$cmd" in
      build) "${compose[@]}" build "$@";;
      start) "${compose[@]}" up -d "$@";;
      stop) "${compose[@]}" stop "$@";;
      logs) "${compose[@]}" logs -f "$@";;
      config) "${compose[@]}" config "$@";;
    esac ;;
  download|verify|restore) exec python3 "$ROOT/scripts/snapshot.py" "$cmd" "$@" ;;
  status) exec python3 "$ROOT/scripts/node-status.py" ;;
  identity|node-id)
    base=${RPC_URL:-http://127.0.0.1:9650}
    bid=zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR
    rpc() {
      local response
      if ! response=$(curl --fail-with-body -sS --max-time 15 "$base/$1" -H 'Content-Type: application/json' --data "$2"); then
        printf '%s\n' "$response" >&2
        echo 'API not ready or request failed. Run: bash vlx-node.sh status' >&2
        return 1
      fi
      printf '%s\n' "$response"
    }
    if [[ "$cmd" == identity ]]; then
      rpc ext/P '{"jsonrpc":"2.0","method":"platform.getBlockchains","params":{},"id":1}' | jq -e --arg bid "$bid" '.result.blockchains[] | select(.id==$bid) | select(.subnetID=="2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv" and .vmID=="u9yY3bLZYo2z79xAfp3ib9WZNpw5GHCtz9RkT5xmdx4KuPGUC")'
    elif [[ "$cmd" == node-id ]]; then
      rpc ext/info '{"jsonrpc":"2.0","method":"info.getNodeID","params":{},"id":1}' | jq -er '.result.nodeID'
    fi ;;
  help|-h|--help)
    echo 'Usage: bash vlx-node.sh init|build|start|stop|logs|config|status|identity|node-id'
    echo '       bash vlx-node.sh download --url https://snapshot.valuex-foundation.com/vlx-l1-chain90000-height-53696-20261020-122850 --cache DIR'
    echo '       bash vlx-node.sh verify --cache DIR'
    echo '       bash vlx-node.sh restore --cache DIR --datadir DIR --confirm-stopped'
    echo 'VLX_ROLE=rpc|validator; VLX_MONITORING=1 to include monitoring.' ;;
  *) echo "Unknown command: $cmd" >&2; exit 1;;
esac
