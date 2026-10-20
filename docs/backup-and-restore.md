# Backup and recovery

A simple copy of a running database, or a hard-linked copy made with `cp -al`, is not treated as an independent, consistent backup. Changes to shared files can also affect a hard-linked copy. Use independent copies and validate them with a restore test.

1. Assign an operator and maintenance window. Record height, NodeID, runtime version and chain configuration.
2. Disable automatic start mechanisms and shut down cleanly with `bash vlx-node.sh stop`. Use the correct `VLX_ROLE` and monitoring mode. Confirm shutdown completion in the logs.
3. Copy the database and chain data to independent storage. Review the actual paths before using this example:

```bash
# Replace SOURCE with the absolute DATA_DIR from the operating configuration.
SOURCE=/srv/vlx-data
DEST=/srv/vlx-backups/CHANGE_ID
sudo mkdir -p "$DEST"
# Omit chainData only after confirming it is absent from this deployment.
sudo tar -cf "$DEST/vlx-db.tar" -C "$SOURCE" db chainData
sudo sha256sum "$DEST/vlx-db.tar"
```

4. Back up TLS/BLS staking keys separately from public snapshots, using encrypted storage with restricted access. Check service size limits and recovery policies when using SSM or Secrets Manager.
5. Store configuration, runtime version/image digest, height and backup hash in the private operational record.
6. Restart the source node and verify identity and health.
7. Test restoration at a separate location on an isolated node. Never run the same validator identity concurrently on two hosts.

Define recovery point objective (RPO), recovery time objective (RTO), backup frequency, retention, remote replication location and recovery owner for your deployment. Creating backups without testing restoration is insufficient. To distribute a backup as a standard snapshot, also follow the [manifest and publication procedure](snapshot-download-and-restore.md).
