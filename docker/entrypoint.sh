#!/usr/bin/env bash
set -euo pipefail
: "${SUBNET_ID:?SUBNET_ID is required}"
[[ "$SUBNET_ID" == "2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv" ]] || { echo 'Unexpected VLX subnet; review network identity' >&2; exit 1; }
role=${NODE_ROLE:-rpc}
[[ "$role" == rpc || "$role" == validator ]] || exit 1
for value in "${HTTP_ALLOWED_HOSTS:-localhost,127.0.0.1,vlx-node}" "${HTTP_ALLOWED_ORIGINS:-http://localhost}"; do
  [[ "$value" != *'*'* ]] || { echo 'Wildcard HTTP policy is forbidden' >&2; exit 1; }
done
keys=(/staking/staker.key /staking/staker.crt /staking/signer.key)
count=0
for key in "${keys[@]}"; do
  if [[ -e "$key" || -L "$key" ]]; then
    [[ -f "$key" && -s "$key" && -r "$key" ]] || {
      echo "Invalid staking key: $key; refusing to regenerate identity" >&2; exit 1;
    }
    count=$((count+1))
  fi
done
if [[ "$role" == validator && "$count" != 3 ]]; then
  echo 'Validator requires existing staker.key, staker.crt and signer.key in host STAKING_DIR' >&2; exit 1
fi
if [[ "$count" != 0 && "$count" != 3 ]]; then
  echo 'Incomplete staking identity; refusing to regenerate missing keys' >&2; exit 1
fi
umask 077
args=(
  --db-dir=/data/db --log-dir=/data/logs --log-level=info
  --network-id="${NETWORK_ID:-1}" --track-subnets="$SUBNET_ID"
  --http-host=0.0.0.0 --http-port=9650 --staking-port=9651
  --http-allowed-hosts="${HTTP_ALLOWED_HOSTS:-localhost,127.0.0.1,vlx-node}"
  --http-allowed-origins="${HTTP_ALLOWED_ORIGINS:-http://localhost}"
  --api-admin-enabled=false --api-metrics-enabled=true
  --plugin-dir=/opt/avalanchego/plugins --partial-sync-primary-network=true
  --chain-config-dir=/config/chains --subnet-config-dir=/config/subnets
)
if [[ "$count" == 3 ]]; then
  args+=(--staking-tls-key-file=/staking/staker.key
         --staking-tls-cert-file=/staking/staker.crt
         --staking-signer-key-file=/staking/signer.key)
fi
[[ -z "${PUBLIC_IP:-}" ]] || args+=(--public-ip="$PUBLIC_IP")
exec /opt/avalanchego/avalanchego "${args[@]}"
