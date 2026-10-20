# RPC node deployment from a snapshot

This procedure deploys a ValueX Chain RPC node from the public repository on Ubuntu 22.04/24.04 LTS or Rocky Linux 9. It does not register a validator.

The snapshot supplies `db` and `chainData`. The repository supplies the Docker image build, VM plugin, Compose configuration and operating tools. After restoration, the node synchronizes blocks created after the checkpoint. This is a starting-data choice, not a separate runtime mode.

## 1. Download the source

Install Git if it is not already available:

```bash
# Ubuntu:
sudo apt-get update
sudo apt-get install -y git
# Rocky Linux 9: use this instead of the Ubuntu commands.
# sudo dnf install -y git
```

```bash
git clone https://github.com/valuex-foundation/vlx-node.git
cd vlx-node
git rev-parse HEAD
sudo bash scripts/install-docker.sh
```

Record the source commit used for deployment. Review scripts before running them with elevated privileges. Run the remaining commands from this directory.

## 2. Configure and build

```bash
bash vlx-node.sh init
chmod 600 .env
vi .env
```

For a new deployment, set these host paths in `.env`:

```dotenv
DATA_DIR=/srv/vlx/data
STAKING_DIR=/srv/vlx/staking
```

Keep `NETWORK_ID=1`, the supplied VLX `SUBNET_ID` and the runtime version aligned with the selected release. Set `PUBLIC_IP` to the reachable address advertised to peers, with the appropriate NAT/firewall configuration. Preserve an existing staking identity when migrating a node.

```bash
sudo bash vlx-node.sh config
sudo bash vlx-node.sh build
```

Do not start the node before restoring the snapshot into its empty data directory. The image installs AvalancheGo and Subnet-EVM; no archived plugin or genesis file needs to be executed or copied over the deployment.

## 3. Download the checkpoint

The following URL selects checkpoint **53696**. Use a different published release URL when deploying another checkpoint, and review its runtime compatibility and metadata.

```bash
sudo bash vlx-node.sh download \
  --url https://snapshot.valuex-foundation.com/vlx-archive-height-53696-20261020-154411 \
  --cache /srv/vlx-snapshots/53696
```

Download performs SHA-256 verification. There is no need to run a separate `verify` command immediately afterward. Reserve space for both the downloaded TAR and the extracted database, plus database growth and logs. This release declares a TAR size of 50,751,211,520 bytes (approximately 47.27 GiB).

This release uses the generated manifest format described in the [snapshot guide](snapshot-download-and-restore.md#generated-manifest-compatibility). Its filename does not establish archive-state availability. Confirm the producing runtime with the publisher; this manifest does not record it. Verify P-Chain identity after startup.

## 4. Restore while the node is stopped

```bash
sudo bash vlx-node.sh stop
sudo docker ps
sudo bash vlx-node.sh restore \
  --cache /srv/vlx-snapshots/53696 \
  --datadir /srv/vlx/data \
  --confirm-stopped
```

The destination must be absent or empty. Stop other AvalancheGo nodes and automatic start mechanisms on this host before restoration. Do not delete an existing database to bypass this check; select a new empty destination and update `DATA_DIR` instead.

The public restore command rechecks the cached archive checksum, validates archive entries, extracts `db` and `chainData` into staging, then moves them into the destination. This step can take substantial disk IO. Wait for `Restored to ...` and a successful command exit. It does not start Docker automatically. See [snapshot format and safety checks](snapshot-download-and-restore.md).

## 5. Start and verify

```bash
sudo bash vlx-node.sh start
sudo bash vlx-node.sh logs
# Ctrl+C stops log viewing only; the containers continue running.
```

In another terminal in the same project directory:

```bash
sudo bash vlx-node.sh status
sudo bash vlx-node.sh identity
```

Require healthy status, both P-Chain and VLX bootstrap completion, matching network identity and EVM Chain ID `90000`. Initial DB loading may precede API availability. If startup fails, inspect logs rather than repeatedly restoring or deleting data. A checksum success alone is not node readiness.

## 6. Test the local RPC gateway

The standard deployment uses **9652**, not the alternate ports used by isolated test deployments. Run these POST requests on the node host:

```bash
curl -sS --max-time 15 http://127.0.0.1:9652/rpc \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'

curl -sS --max-time 15 http://127.0.0.1:9652/rpc \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":2,"method":"eth_blockNumber","params":[]}'

curl -sS --max-time 15 http://127.0.0.1:9652/rpc \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":3,"method":"eth_getBlockByNumber","params":["latest",false]}'
```

Expected chain ID: `0x15f90`. For this checkpoint, the accepted height must be at least `0xd1c0` (53696). Compare the latest block height and hash with a trusted network reference; a checkpoint-height response alone does not prove the node is at the network head. A browser address-bar GET is not an RPC test.

## 7. Connect exchange infrastructure

For remote applications, configure the [HTTPS proxy and firewall](ports-and-firewall.md) and use `https://YOUR_RPC_DOMAIN/rpc`. Keep ports 9650 and 9652 bound to loopback. For temporary access, use an SSH tunnel. Browser-based test pages need a same-origin proxy or an explicitly configured origin policy; opening a local HTML file does not bypass CORS.

Review the [RPC method allowlist](rpc-methods.md), [monitoring runbook](../monitoring/README.md) and [backup procedure](backup-and-restore.md). Define deposit confirmations, reorganization handling, service access and historical-state requirements with the exchange. Snapshot classification does not automatically establish archive-state availability.

## Normal restart

```bash
sudo bash vlx-node.sh stop
sudo bash vlx-node.sh start
sudo bash vlx-node.sh status
```

Normal restarts reuse the existing database and staking keys. Do not download or restore the snapshot again for each restart.
