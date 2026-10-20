# Configuration and versions

`versions.env`, `.env.example`, the Dockerfile and Compose default to `v1.15.0`. A value supplied through `.env` or the shell can override `AVALANCHEGO_VERSION`; record the actual build version in your deployment log. Subnet-EVM is downloaded from the same AvalancheGo release. There is no separate `SUBNET_EVM_VERSION` build argument. Review the [official upgrade considerations](https://build.avax.network/docs/avalanche-l1s/upgrade/considerations).

| Variable | Meaning |
|---|---|
| `NETWORK_ID` | Avalanche network; `1` for mainnet |
| `SUBNET_ID` | VLX Subnet ID; validate with `identity` after bootstrap |
| `PUBLIC_IP` | Public address advertised by the node |
| `DATA_DIR` | Host parent directory for db/chainData/logs |
| `STAKING_DIR` | Persistent host directory for TLS key, certificate and BLS key |
| `HTTP_ALLOWED_HOSTS` | Default localhost,127.0.0.1,vlx-node; wildcards rejected |
| `HTTP_ALLOWED_ORIGINS` | Default http://localhost; wildcards rejected |
| `PROMETHEUS_RETENTION` | Default 15d; adjust to storage capacity |
| `GRAFANA_ADMIN_PASSWORD` | Required when monitoring is enabled; keep private |

`VLX_ROLE=rpc|validator` and `VLX_MONITORING=1` are shell variables passed when invoking the helper. Adding them to `.env` alone does not change the helper's selected role or monitoring mode.

Chain configuration lives at `config/chains/<Blockchain ID>/config.json`. The `.example` file is not activated automatically. It currently illustrates archive operation with pruning and state sync disabled. Copy it only when that behavior is required. Disabling pruning does not recover historical state that has already been removed. Distinguish block/transaction history from the ability to query account or contract state at old blocks. Check snapshot classification in the release metadata; `unknown` does not establish historical-state availability.

The genesis file describes the existing chain. Do not create a new chain from the local genesis file merely to join the production network. Existing data, backups and `.env` files are not migrated automatically.

## Which version file is used?

| File or input | Consumer | Purpose |
|---|---|---|
| `versions.env` | `.github/workflows/docker-build.yml` | Version pinned for CI image builds; loaded into the GitHub Actions environment |
| `.env.example` | `bash vlx-node.sh init` | Public template copied to `.env` only if `.env` does not exist |
| `.env` | Local Docker Compose | Deployment-specific image build version and node settings |
| Shell `AVALANCHEGO_VERSION` | Local Docker Compose | Overrides the value from `.env` for that invocation |
| Compose/Dockerfile defaults | Builds without an explicit version | Fallback version |

It is correct to keep `AVALANCHEGO_VERSION` in `.env.example`. `versions.env` is also in use, but local Compose does **not** load it automatically. Editing only `versions.env` changes the CI build pin, not an existing deployment's `.env`. Editing `.env.example` does not update an existing `.env` either.

For a coordinated release, update the CI pin, template and fallback defaults together. Review each operating `.env` and rebuild/recreate the node during the approved maintenance window. Changing a variable alone does not replace an already built or running image. These variables select the node runtime version, not the EVM Chain ID.
