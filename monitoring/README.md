# Monitoring runbook

## Startup and access

Set `GRAFANA_ADMIN_PASSWORD` in `.env`, then run `sudo env VLX_MONITORING=1 bash vlx-node.sh start`. Also set `VLX_ROLE=validator` for a validator. Use the same monitoring selection when stopping the services.

Prometheus scrapes `vlx-node:9650`, `vlx-probe:9101` and `node-exporter:9100` over the Compose network, without relying on `host.docker.internal`. Grafana provisions the supplied data source and dashboard automatically.

```bash
ssh -L 9090:127.0.0.1:9090 -L 3000:127.0.0.1:3000 ADMIN@HOST
```

Open the Targets page at localhost:9090 and the VLX operations dashboard at localhost:3000. The initial Grafana username is `admin`, with the password supplied through the operating `.env`. Changing that variable does not automatically change the password in an existing Grafana data volume; use the Grafana account-management interface.

Prometheus retention defaults to `15d` and is configurable through `.env`. Named volumes preserve monitoring data. Do not run `docker compose down -v` in production: it removes those volumes. Confirm retention and storage capacity using observed disk usage.

## Metrics and operating policies

The placeholders below are deployment-specific configuration fields, not a record of repository test results. Set them using observed VLX block intervals and your operating policy. Keep recipient details in your internal runbook.

| Signal | Collection or inspection | Required policy |
|---|---|---|
| Bootstrap completion | `vlx_bootstrapped` | Expected true; initial-sync grace period [Operator confirmation required] |
| Health and chain errors | `vlx_health`, node logs, `/ext/health` | Failure-specific response and duration [Operator confirmation required] |
| RPC block height | `vlx_rpc_block_number` | Compare with a reference node; stall duration [Operator confirmation required] |
| Accepted height | Inspect `/ext/metrics` for the actual VLX chain metric and labels | Metric name and stall criterion [Verification required] |
| Processing blocks | Inspect chain consensus metrics under `/ext/metrics` | Metric name and persistence threshold [Verification required] |
| Container restarts | Docker `RestartCount`, `process_start_time_seconds` | Count and time window [Operator confirmation required] |
| Free disk space | `node_filesystem_avail_bytes` / `node_filesystem_size_bytes` | Warning/critical ratios and absolute capacity [Operator confirmation required] |
| IO wait | `rate(node_cpu_seconds_total{mode="iowait"}[5m])` | Duration and ratio [Operator confirmation required] |
| Available memory | `node_memory_MemAvailable_bytes` | Warning/critical thresholds [Operator confirmation required] |
| Collection failure | `up`, `*_probe_success` | Current rules warn immediately; grace period [Operator confirmation required] |

For accepted height and processing blocks, inspect the actual v1.15.0 VLX metrics and verify metric names and chain labels before adding dashboard panels and alerts. Use only metric names and labels confirmed on the deployed runtime. The included dashboard covers bootstrap, health, RPC height, scrape availability, disk, memory, IO wait and process start time. Process start time is not the same measurement as the container's restart count.

```bash
curl -fsS http://127.0.0.1:9650/ext/metrics > metrics-local.txt
sudo docker compose ps -q vlx-node | xargs -r sudo docker inspect --format '{{.RestartCount}} {{.State.Status}} {{.State.OOMKilled}}'
```

Raw operational metrics can contain infrastructure details; do not commit them to the public repository.

## Alert evaluation and delivery

`alert-rules/availability.yml` evaluates scrape failure, health failure and RPC probe failure in Prometheus. Health warnings can occur during bootstrapping. Add block-stall, processing-duration and disk-threshold rules only after approving their operating policies.

The supplied configuration does not include external messaging credentials or an Alertmanager receiver. **A firing Prometheus alert does not mean an operator has received a notification.** Configure contact points, notification policies and alert rules based on these PromQL expressions in Grafana Alerting, or connect an operational Alertmanager. Prometheus rules are not automatically converted into Grafana-managed notification rules.

- Primary recipient and channel: **[Operator confirmation required]**. Store names and contact details in private operations documentation.
- Secondary escalation and out-of-hours owner: **[Operator confirmation required]**.
- Acknowledgment deadline and incident severity policy: **[Operator confirmation required]**.
- Owner for recurring delivery tests and evidence: **[Operator confirmation required]**.

Inject tokens through a controlled secret store such as Secrets Manager or SSM, never public YAML. Mark alerting operational only after a real test notification has been received and acknowledged.

## Incident response

1. Acknowledge the alert, assign an owner and check maintenance or initial-bootstrap status.
2. Use target availability and probe success metrics to distinguish node failures from monitoring failures.
3. Inspect `status`, logs, reference-node height, peers, storage, memory and OOM events.
4. For low disk space, review expansion, log policy and retention. Do not delete database files as a workaround.
5. For persistent processing or chain errors, check versions and recent changes, then escalate to the responsible operator.
6. Confirm key availability and an independent backup before restarting or restoring.
7. Verify health, height progress and alert resolution. Record the incident timeline and follow-up actions.
