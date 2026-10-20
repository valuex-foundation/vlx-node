# Bootstrapping

Choose **sync from scratch** or **restore from snapshot** in the [quickstart](quickstart.md#choose-a-bootstrap-method). Both methods use the same node deployment.

The node starts with `partial-sync-primary-network=true`: it synchronizes P-Chain but skips X-Chain and C-Chain. P-Chain tracks chain registration and validator information needed by the L1 node. This option does not bypass P-Chain history when starting with an empty database. Restoring a compatible P-Chain database can shorten initialization; synchronization continues from the restored state.

Verify P-Chain and VLX bootstrap and health status separately. Synchronization time depends on peers, disk performance, database state and network conditions; no fixed completion time is guaranteed.

```bash
bash vlx-node.sh status
sudo bash vlx-node.sh logs
```

Check `info.isBootstrapped`, health and RPC block height together. If failures persist, inspect logs, storage and memory. Assess a stalled height against actual block production intervals, transaction activity and a trusted reference node. The stall-duration threshold is **[Operator confirmation required]**. For snapshot-based recovery, follow the [snapshot procedure](snapshot-download-and-restore.md).

## HTTP 503 during initial startup

The P-Chain can reject `platform.getBlockchains` until bootstrapping finishes.
The health endpoint can also return HTTP 503 while bootstrap checks fail.
The status helper preserves these diagnostics and checks P-Chain and VLX bootstrap
independently; it exits nonzero until health, both bootstrap checks, EVM Chain ID
and block-height queries all pass.

```bash
sudo docker compose logs --since=5m vlx-node 2>&1 |
  grep -E 'fetching blocks|executing blocks|bootstrapping|ERROR|FATAL'
```

Increasing `numFetchedBlocks` / `pctComplete` indicates download progress.
The logged `eta` is an estimate for that phase, not a guarantee of service readiness.
A fresh database can require substantial P-Chain synchronization even with partial
primary-network sync enabled. Do not delete the database, repeatedly restart the node,
or lower stake health thresholds to suppress an initial-bootstrap warning.

Connected peer count and connected validator stake are different measurements.
A large peer count alone does not satisfy the chain's stake health check.
If progress stops or stake connectivity remains insufficient after bootstrap,
investigate peer reachability and recent errors.
