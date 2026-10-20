# Installation on Ubuntu and Rocky Linux

## Target environments

The installation script targets Ubuntu 22.04/24.04 LTS and Rocky Linux 9. Image build paths are provided for Linux amd64 and arm64. Use 8 CPU cores, 16 GiB RAM and NVMe storage as an initial capacity-planning reference, then size for extracted snapshot data, database growth, logs and independent backups. These are not guaranteed capacity requirements.

Run commands from the project root. Scripts require Bash. If executable permissions are missing after extracting a ZIP, use `bash vlx-node.sh`.

## 1. Install dependencies

Review the script before running it on a new host. It does not automatically remove conflicting Docker or Podman packages.

```bash
sudo bash scripts/install-docker.sh
sudo docker run --rm hello-world
sudo docker compose version
```

Ubuntu uses Docker's Ubuntu APT repository. Rocky 9 uses Docker's CentOS RPM repository. Rocky is not the same distribution as CentOS in Docker's official support matrix, so validate the deployment on your chosen Rocky image. Rocky 8 and 10 are outside the installation script's scope. The script does not automatically add users to the Docker group, which effectively grants root-level access.

References: [Docker on Ubuntu](https://docs.docker.com/engine/install/ubuntu/), [Docker on CentOS](https://docs.docker.com/engine/install/centos/).

## 2. Configure and build an RPC node

```bash
bash vlx-node.sh init
chmod 600 .env
# Edit and review .env before continuing.
sudo bash vlx-node.sh config
sudo bash vlx-node.sh build
```

Set `PUBLIC_IP` to the public address advertised by the node. Absolute paths are recommended for `DATA_DIR` and `STAKING_DIR`; defaults `./data` and `./staking` are relative to the project root. Existing `.env` files are preserved, so compare yours with `.env.example` and update the Subnet ID where necessary. The `config` output can contain credentials; do not paste it into public issues.

Keys generated in RPC mode persist in the host staking directory. Configure public HTTPS separately using the [ports and firewall guide](ports-and-firewall.md).

### Choose a bootstrap method

Both methods use the same downloaded source package, `docker-compose.yml`, `deploy/compose.rpc.yml`, image and scripts. The difference is the starting database, not a different deployment package. Choose one method before starting.

### Option A: Sync from scratch

Start with an empty `DATA_DIR`. The node synchronizes P-Chain and then VLX. The configured `partial-sync-primary-network=true` skips X-Chain and C-Chain; it does not skip P-Chain history.

```bash
sudo bash vlx-node.sh start
sudo bash vlx-node.sh logs
```

See [bootstrapping and progress diagnostics](bootstrapping.md). Downloading blocks, executing blocks and completing bootstrap are separate stages.

### Option B: Restore from snapshot

For the complete clone, configuration, restore and exchange RPC workflow, see [RPC node deployment from a snapshot](exchange-snapshot-setup.md).

Follow the [snapshot download and restoration guide](snapshot-download-and-restore.md) for storage requirements, checksum verification and safe restoration. The commands below use example host paths; ensure they match your deployment.

```bash
sudo bash vlx-node.sh download \
  --url https://snapshot.valuex-foundation.com/vlx-l1-chain90000-height-53696-20261020-122850 \
  --cache /srv/vlx-snapshots/53696
# Download already verifies the checksum. An extra "verify" command is optional.
sudo bash vlx-node.sh stop
# Stop any other node processes before restoring. Destination must be empty.
sudo bash vlx-node.sh restore --cache /srv/vlx-snapshots/53696 \
  --datadir /srv/vlx-data-restored --confirm-stopped
# Set DATA_DIR=/srv/vlx-data-restored in .env; preserve STAKING_DIR.
sudo bash vlx-node.sh start
sudo bash vlx-node.sh logs
```

The restore command verifies the archive again, checks every archive entry, extracts only `db` and `chainData`, and places the completed data directory at the target path. It does not start the node. The snapshot does not replace the Docker image, plugins, deployment configuration or staking keys. A compatible P-Chain database can reduce initial synchronization, but the node must still catch up after restoration.

### Verify readiness after either method

```bash
sudo bash vlx-node.sh status
sudo bash vlx-node.sh identity
curl -sS --max-time 15 http://127.0.0.1:9652/rpc \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
curl -sS --max-time 15 http://127.0.0.1:9652/rpc \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":2,"method":"eth_blockNumber","params":[]}'
```

The expected chain ID is `0x15f90` (90000). Require successful P-Chain and VLX bootstrap, healthy status and progress toward the network head, not just a chain-ID response. See [RPC methods](rpc-methods.md). Port `9652` is the standard RPC gateway; isolated experiments may use different host ports.

An unhealthy result can occur during initial bootstrapping; inspect logs and progress rather than assuming every health failure is expected.

## 3. Verify validator identity persistence

Validator mode requires `staker.key`, `staker.crt` and `signer.key` in the host `STAKING_DIR`. Startup is rejected when any file is missing. To migrate keys previously stored under `/config`, shut down cleanly, copy the same files to the new staking directory and restrict access. Do not replace an existing validator's identity with newly generated keys.

For a new validator, generate keys in RPC mode first or use an approved offline procedure. Verify persistence before registration. Validator registration itself is a separate P-Chain/L1 operation and is not performed by these scripts.

```bash
sudo bash vlx-node.sh node-id > node-id.before.txt
sudo bash vlx-node.sh stop
# Check all three host key files, their permissions and a secure backup.
sudo env VLX_ROLE=validator bash vlx-node.sh start --force-recreate --remove-orphans
sudo bash vlx-node.sh node-id > node-id.after.txt
diff -u node-id.before.txt node-id.after.txt
sudo bash vlx-node.sh identity
sudo bash vlx-node.sh status
```

Retry `node-id` after the API becomes available if necessary. If the NodeID changes, stop registration. Compare the host `signer.key` checksum before and after recreation in your internal operational record as well. Do not publish key material or those records. Never run two hosts concurrently with the same validator identity. During an RPC-to-validator transition, `--remove-orphans` removes the old gateway. Continue setting `VLX_ROLE=validator` for subsequent validator lifecycle commands.

## 4. Enable monitoring

Set a strong `GRAFANA_ADMIN_PASSWORD` in `.env`, then run:

```bash
sudo env VLX_ROLE=validator VLX_MONITORING=1 bash vlx-node.sh start
# Use VLX_ROLE=rpc for an RPC node.
```

Complete the receiver configuration, threshold decisions and delivery tests in the [monitoring runbook](../monitoring/README.md) before declaring monitoring operational.

## Deployment acceptance checklist

Use this checklist on each target operating system and architecture. Record results, runtime versions and timestamps in your deployment records.

- [ ] Build the image, validate Compose configuration and start the services.
- [ ] Verify network identity, EVM Chain ID, P-Chain/VLX bootstrap and health.
- [ ] Confirm the same NodeID and BLS key after container recreation.
- [ ] Test externally that management ports are blocked and HTTPS 443 works.
- [ ] Confirm Admin/debug methods and mixed batches containing prohibited methods are rejected.
- [ ] Test snapshot restoration at a separate location when using snapshots.
- [ ] Confirm Prometheus targets are UP and a test alert reaches its recipient.
- [ ] On Rocky Linux, verify mounts, collectors and proxy access with SELinux enforcing.
