#!/usr/bin/env python3
"""Report bootstrap progress even when health returns HTTP 503."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import textwrap
import urllib.error
import urllib.request

BID = "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR"


def restore_history(target):
    print("SNAPSHOT HISTORY")
    print("Configured local directory; not proof of the running container mount.")
    try:
        if target is None:
            raise ValueError("Data directory unavailable")
        raw = (target / ".vlx-restore.json").read_text(encoding="utf-8")
        record = json.loads(raw)
        if (not isinstance(record, dict) or record.get("state") != "restored"
                or type(record.get("height")) is not int or record["height"] < 0
                or not isinstance(record.get("file"), str)
                or not isinstance(record.get("completedAt"), str)):
            raise ValueError("Invalid restore record")
        print("  Snapshot: RESTORE COMPLETED (local restore record)")
        print(f"  VLX checkpoint: {record['height']} (not the current P-Chain height)")
        print(f"  Archive: {record['file']}")
        print(f"  Completed at: {record['completedAt']}")
        print("  File restoration is complete; live bootstrap and RPC readiness are checked separately.")
    except (OSError, ValueError):
        print("  Restore record: NOT AVAILABLE")
        print("  Older/manual restores may have no record. This does not mean sync from scratch or restore failure; do not restore again just to create a record.")
    print()


def configured_data_dir():
    root = Path(__file__).resolve().parents[1]
    role = os.environ.get("VLX_ROLE", "rpc")
    if role not in ("rpc", "validator"):
        return None
    command = ["docker", "compose", "--project-directory", str(root),
               "-f", str(root / "docker-compose.yml"),
               "-f", str(root / "deploy" / f"compose.{role}.yml")]
    if os.environ.get("VLX_MONITORING") == "1":
        command += ["-f", str(root / "deploy/compose.monitoring.yml")]
    try:
        config = json.loads(subprocess.check_output(command + ["config", "--format", "json"],
                           stderr=subprocess.DEVNULL, text=True, timeout=15))
        for mount in config["services"]["vlx-node"]["volumes"]:
            if mount.get("target") == "/data/db" and mount.get("type") == "bind":
                return Path(mount["source"]).parent
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        pass
    return None


def request(base, path, method=None, params=None):
    payload = None if method is None else json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method,
        "params": [] if params is None else params,
    }).encode()
    req = urllib.request.Request(base.rstrip("/") + path, payload,
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            code, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, exc.read()
    except (OSError, urllib.error.URLError) as exc:
        return 0, {"error": {"message": str(exc)}}
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("Expected JSON object")
    except (ValueError, UnicodeError):
        body = {"error": {"message": raw.decode("utf-8", errors="replace")[:300]}}
    return code, body


def error_text(code, body):
    error = body.get("error", {})
    message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
    return f"HTTP {code}: {message or 'invalid or unavailable response'}"


def object_value(value):
    return value if isinstance(value, dict) else {}


def assess_stage(health_code, checks, peers, bootstrap, vlx_missing, ready):
    """Describe observed readiness, without claiming progress from one sample."""
    if ready:
        stage = "READY"
        detail = "Health, P-Chain, VLX bootstrap and basic RPC checks passed."
    elif health_code == 0:
        stage = "API_UNREACHABLE"
        detail = "Check the container, RPC_URL and startup logs; the node may still be starting."
    elif any(object_value(checks.get(key)).get("error") == "not yet run"
             for key in ("P", "bootstrapped")):
        stage = "INITIALIZING"
        detail = "Health checks have not run yet. Database loading or startup may still be in progress."
    elif peers == 0:
        stage = "WAITING_FOR_PEERS"
        detail = "No peer connections reported. Check startup logs, outbound connectivity and firewall settings."
    elif bootstrap.get("P") is False:
        stage = "P_CHAIN_BOOTSTRAPPING"
        detail = "P-Chain is not bootstrapped. This single sample does not prove forward progress; compare fetching/executing block logs over time."
    elif vlx_missing and bootstrap.get("P") is True:
        stage = "VLX_CHAIN_UNAVAILABLE"
        detail = "P-Chain is bootstrapped but VLX is not registered yet. Check SUBNET_ID, VM plugin and chain startup logs if this persists."
    elif bootstrap.get("VLX") is False:
        stage = "VLX_BOOTSTRAPPING"
        detail = "VLX bootstrap has not completed. Compare VLX bootstrap logs over time to confirm progress."
    elif bootstrap.get("P") is True and bootstrap.get("VLX") is True:
        stage = "HEALTH_OR_RPC_CHECK_FAILED"
        detail = "Both chains are bootstrapped; inspect the health and RPC results above before serving requests."
    else:
        stage = "READINESS_UNCONFIRMED"
        detail = "Some readiness checks are unavailable. Inspect the responses above and startup logs."
    if vlx_missing and bootstrap.get("P") is not True:
        detail += " VLX is not registered yet; RPC may return 404 before chain startup."
    return stage, detail


def row(label, result, detail=""):
    # Keep multiline API errors and terminal control characters out of table cells.
    clean = lambda value: " ".join("".join(c if c.isprintable() else " " for c in str(value)).split())
    print(f"{label:<29} {clean(result):<13} {clean(detail)}".rstrip())


def status(base, snapshots=False):
    print("ValueX | Node Diagnostics", flush=True)
    print("-" * 72)
    print("Checking health, bootstrap and RPC (15s timeout per request)...", flush=True)
    health_code, body = request(base, "/ext/health")
    healthy = health_code == 200 and body.get("healthy") is True
    checks = object_value(body.get("checks"))
    network = object_value(object_value(checks.get("network")).get("message"))
    peers = network.get("connectedPeers", "UNAVAILABLE")
    pcheck = object_value(checks.get("P"))
    percent = object_value(object_value(pcheck.get("message")).get("networking")).get("percentConnected")
    bootstrap = {}
    bootstrap_details = {}
    vlx_missing = False
    for label, chain in (("P", "P"), ("VLX", BID)):
        code, result = request(base, "/ext/info", "info.isBootstrapped", {"chain": chain})
        value = object_value(result.get("result")).get("isBootstrapped")
        bootstrap[label] = value if code == 200 and isinstance(value, bool) else None
        bootstrap_details[label] = "" if bootstrap[label] is not None else error_text(code, result)
        if label == "VLX":
            vlx_missing = "there is no chain with alias/ID" in error_text(code, result)
    rpc_rows = []
    chain_ok = height_ok = False
    for method, label in (("eth_chainId", "EVM chain ID"), ("eth_blockNumber", "Latest block")):
        code, result = request(base, f"/ext/bc/{BID}/rpc", method)
        value = result.get("result")
        if code != 200 or not isinstance(value, str) or "error" in result:
            rpc_rows.append((label, "UNAVAILABLE", error_text(code, result)))
        elif method == "eth_chainId":
            chain_ok = value.lower() == "0x15f90"
            rpc_rows.append((label, "PASS" if chain_ok else "MISMATCH", f"{value} (expected 0x15f90 / 90000)"))
        else:
            try:
                height = int(value, 16)
                height_ok = height >= 0
                rpc_rows.append((label, "PASS" if height_ok else "INVALID", f"{height} ({value})"))
            except ValueError:
                rpc_rows.append((label, "INVALID", "Invalid block height response"))
    ready = healthy and all(bootstrap.get(k) is True for k in ("P", "VLX")) and chain_ok and height_ok
    stage, assessment = assess_stage(health_code, checks, peers, bootstrap, vlx_missing, ready)
    print(f"\nREADINESS     {'READY' if ready else 'NOT READY'}")
    print(f"STAGE         {stage}")
    print(f"ENDPOINT      {base}\n")
    row("CHECK", "RESULT", "DETAIL")
    row("Health", "PASS" if healthy else "UNAVAILABLE" if health_code == 0 else "NOT READY", f"HTTP {health_code}" if health_code else error_text(health_code, body))
    for key, label in (("P", "P-Chain bootstrap"), ("VLX", "VLX bootstrap")):
        value = bootstrap[key]
        row(label, "COMPLETE" if value is True else "INCOMPLETE" if value is False else "UNAVAILABLE", bootstrap_details[key])
    row("Connected peers", peers)
    row("P-Chain connected stake", f"{percent * 100:.2f}%" if type(percent) in (int, float) else "UNAVAILABLE")
    for values in rpc_rows:
        row(*values)
    for label in ("P", "bootstrapped"):
        error = object_value(checks.get(label)).get("error")
        if error:
            row(f"Health / {label}", "DETAIL", error)
    if not healthy and not checks and health_code:
        row("Health response", "DETAIL", error_text(health_code, body))
    print()
    if snapshots:
        restore_history(configured_data_dir())
    print("ASSESSMENT")
    print(textwrap.fill(assessment, width=72))
    if not ready:
        print("Forward progress and ETA cannot be determined from a single check.")
    print("\nACTION")
    if ready:
        print("Check block advancement over time before accepting RPC traffic.")
    else:
        print("Inspect recent logs and compare bootstrap progress:")
        print("sudo bash vlx-node.sh logs --since 5m --tail 100")
        print("Do not reset or restore the database based only on this status.")
    print(f"\nEXIT CODE     {0 if ready else 1} - {'Readiness checks passed' if ready else 'Readiness checks have not passed'}")
    print("-" * 72)
    return 0 if ready else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", action="store_true",
                        help="Include local snapshot restore history (no archive scan or verification)")
    args = parser.parse_args(argv)
    try:
        return status(os.environ.get("RPC_URL", "http://127.0.0.1:9650"), snapshots=args.snapshots)
    except KeyboardInterrupt:
        print("\nStatus check cancelled. The node was not stopped.", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
