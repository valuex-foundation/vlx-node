# Upgrade and rollback

1. Review official release notes, network activation schedules and database/VM compatibility.
2. Keep `versions.env`, Dockerfile defaults, `.env.example`, Compose defaults and the live `.env` aligned with the tested version. CI does not pass a separate VM build argument.
3. On a test node, verify the image build, plugin execution, chain identity, RPC and bootstrapping. Validate amd64 and arm64 separately if both will be distributed.
4. During a maintenance window, shut down cleanly and create an [independent backup](backup-and-restore.md). Preserve the previous image ID/digest, keys and configuration.
5. Build and start the new version, then verify NodeID, BLS key, health, height, logs and monitoring.

```bash
sudo bash vlx-node.sh stop
# Complete the backup and review the runtime version in .env.
sudo bash vlx-node.sh build
sudo bash vlx-node.sh start --force-recreate
sudo bash vlx-node.sh status
```

For validators, invoke lifecycle commands with `sudo env VLX_ROLE=validator ...`. Include `VLX_MONITORING=1` when managing monitoring services.

If the new runtime changes the database, do not simply point the previous binary at that database. When compatibility is unverified, restore the pre-upgrade database backup to a separate location and use the previous image with the same staking identity. A mandatory network upgrade may make downgrade impossible, so establish an approved recovery route before changing versions.

Document rollback triggers, the approval owner and the target recovery time before the maintenance window.
