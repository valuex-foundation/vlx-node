# Troubleshooting

| Symptom | Checks and response |
|---|---|
| Unexpected VLX subnet | Compare the existing .env with the P-Chain response; the helper preserves existing configuration |
| Missing validator keys | Check all three files in STAKING_DIR; restore the established identity rather than generating replacements |
| API access rejected | Check loopback bindings, allowed Host values and Nginx/gateway routing |
| Persistent bootstrap/health failure | Inspect status/logs, peers, disk IO/capacity and VM version/execution |
| HTTP 503 / chain is not done bootstrapping | Run `status` and compare successive bootstrap progress logs; P-Chain identity queries are unavailable until bootstrap finishes |
| Docker says healthy while HTTP health is 503 | Use the updated Compose healthcheck with pipefail and a nonempty JSON check; recreate the service during a planned restart |
| Plugin build failure | Verify v1.15.0 release assets, architecture and download connectivity |
| Existing-data error during restore | Use a new empty destination; do not delete the current database to bypass the guard |
| Snapshot checksum mismatch | Compare the publisher's manifest and SHA256SUMS, then download again |
| Unsupported archive layout | Publisher must validate db/chainData roots and exclude links/devices before repackaging |
| Permission denied on Rocky | Inspect SELinux AVCs, mount labels and host permissions; do not disable SELinux globally |
| Prometheus target DOWN | Check Compose service names, HTTP Host policy and container logs |
| Grafana startup failure | Check GRAFANA_ADMIN_PASSWORD and data-volume permissions |
| Changed NodeID | Stop registration/operation and restore the established staking path and keys |

```bash
sudo bash vlx-node.sh logs
sudo bash vlx-node.sh status
sudo docker compose ps
sudo journalctl -u docker --since '30 minutes ago'
# Rocky Linux: inspect SELinux denials.
sudo ausearch -m AVC -ts recent
```

Include version, OS/architecture, timestamps with timezone, and redacted logs in incident reports. Do not post live `.env` files, keys, contact details or operational IP inventories in public issues.
