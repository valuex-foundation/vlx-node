<p align="center">
  <img src="docs/assets/logo-full.png" alt="ValueX">
</p>

# ValueX Chain Node

Docker Compose configuration, installation scripts and operating guides for ValueX Chain (VLX) nodes. The installation scripts target Ubuntu 22.04/24.04 LTS and Rocky Linux 9.

| Identifier             | Value                                                |
| ---------------------- | ---------------------------------------------------- |
| AvalancheGo Network ID | `1` (Avalanche mainnet)                              |
| EVM Chain ID           | `90000` (`0x15f90`)                                  |
| Blockchain ID          | `zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR`  |
| Subnet ID              | `2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv` |
| VM ID                  | `u9yY3bLZYo2z79xAfp3ib9WZNpw5GHCtz9RkT5xmdx4KuPGUC`  |

Run `sudo bash vlx-node.sh identity` after bootstrapping to verify the Blockchain ID, Subnet ID and VM ID against P-Chain.

## Quick start

Obtain the source from `valuex-foundation/vlx-node` or extract a public source package. Run the following commands from the project root on your Linux server.

```bash
sudo bash scripts/install-docker.sh
bash vlx-node.sh init
# Review SUBNET_ID, PUBLIC_IP, DATA_DIR and STAKING_DIR in .env.
sudo bash vlx-node.sh build
# Choose a bootstrap method below before starting the node.
```

Both methods use the **same source package, Docker image and Compose deployment**:

| Bootstrap method      | Starting data                                                   | Instructions                                                                           |
| --------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Sync from scratch     | Empty database; synchronize P-Chain, then VLX                   | [Quickstart: sync from scratch](docs/quickstart.md#option-a-sync-from-scratch)         |
| Restore from snapshot | Restore `db` and `chainData`, then synchronize remaining blocks | [Quickstart: restore from snapshot](docs/quickstart.md#option-b-restore-from-snapshot) |

`partial-sync-primary-network=true` skips X-Chain and C-Chain synchronization; P-Chain synchronization is still required. A snapshot can shorten initialization if it contains a compatible P-Chain database. See [bootstrapping](docs/bootstrapping.md).

After preparing the data using your chosen method:

```bash
sudo bash vlx-node.sh start
sudo bash vlx-node.sh status
sudo bash vlx-node.sh identity
```

Existing `.env` files are preserved. Update any outdated Subnet ID manually. The scripts require Bash; invoke them with `bash`, not `sh`.

## Layout and documentation

- `docker/`: Dockerfile and entrypoint; AvalancheGo and Subnet-EVM from release `v1.15.0`.
- `docker-compose.yml`: shared node service, loopback RPC binding and persistent staking identity.
- `deploy/`: RPC, validator and monitoring overrides; Nginx HTTPS example.
- `scripts/`: installation, node operations, snapshot verification/restoration and public packaging.
- `config/`, `genesis/`, `chainlist/`: public configuration examples and chain metadata.
- `monitoring/`: scraping, alert rules, Grafana provisioning and dashboard.

[Installation and validator keys](docs/quickstart.md) | [Network identity](docs/network-identity.md) | [Ports and HTTPS](docs/ports-and-firewall.md) | [Configuration](docs/configuration.md) | [Bootstrapping](docs/bootstrapping.md) | [Snapshots](docs/snapshot-download-and-restore.md) | [Backups](docs/backup-and-restore.md) | [Upgrades](docs/upgrade-and-rollback.md) | [RPC methods](docs/rpc-methods.md) | [Monitoring](monitoring/README.md) | [Troubleshooting](docs/troubleshooting.md)

## Snapshots

Snapshots are distributed through [snapshot.valuex-foundation.com](https://snapshot.valuex-foundation.com). Follow the [snapshot restoration guide](docs/snapshot-download-and-restore.md) to select a release, verify its checksum and restore the database. Release metadata describes the checkpoint height, runtime version and data format. Historical-state availability depends on the selected snapshot and pruning configuration.

## Operations

Before exposing an RPC endpoint, verify network identity, bootstrap completion, health and block progress using the [deployment checklist](docs/quickstart.md#deployment-acceptance-checklist). Configure HTTPS and access controls with the [ports and firewall guide](docs/ports-and-firewall.md), and enable [monitoring](monitoring/README.md).

Keep staking keys, credentials and live `.env` files outside version control. See [SECURITY.md](SECURITY.md) for security guidance and [CONTRIBUTING.md](CONTRIBUTING.md) for contributions.

## Development

Run the regression tests and build source packages:

```bash
python3 -m unittest discover -s tests
python3 scripts/package-public.py
```

The packaging script produces equivalent ZIP, TAR and TAR.GZ source archives under `dist/`. Blockchain snapshots and private operational files are not included.
