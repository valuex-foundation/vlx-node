#!/usr/bin/env python3
"""Report bootstrap progress even when health returns HTTP 503."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

BID = "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR"


def restore_history(target):
    print("Snapshot history (configured local data directory; not proof of the running node's mount):")
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
        print("  File restoration is complete; live bootstrap and RPC readiness are checked separately below.")
    except (OSError, ValueError):
        print("  Snapshot: UNKNOWN (no readable valid restore record)")
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


def explain_stage(health_code, checks, peers, bootstrap, vlx_missing, ready):
    """Describe observed readiness, without claiming progress from one sample."""
    if ready:
        stage = "READY"
        detail = "Health, P-Chain, VLX bootstrap and basic RPC checks passed."
    elif health_code == 0:
        stage = "API UNREACHABLE"
        detail = "Check the container, RPC_URL and startup logs; the node may still be starting."
    elif any(object_value(checks.get(key)).get("error") == "not yet run"
             for key in ("P", "bootstrapped")):
        stage = "INITIALIZING"
        detail = "Health checks have not run yet. Database loading or startup may still be in progress."
    elif peers == 0:
        stage = "WAITING FOR PEERS"
        detail = "No peer connections reported. Check startup logs, outbound connectivity and firewall settings."
    elif bootstrap.get("P") is False:
        stage = "P-CHAIN BOOTSTRAP INCOMPLETE"
        detail = "P-Chain is not bootstrapped. This single sample does not prove forward progress; compare fetching/executing block logs over time."
    elif vlx_missing and bootstrap.get("P") is True:
        stage = "VLX CHAIN UNAVAILABLE"
        detail = "P-Chain is bootstrapped but VLX is not registered yet. Check SUBNET_ID, VM plugin and chain startup logs if this persists."
    elif bootstrap.get("VLX") is False:
        stage = "VLX BOOTSTRAP INCOMPLETE"
        detail = "VLX bootstrap has not completed. Compare VLX bootstrap logs over time to confirm progress."
    elif bootstrap.get("P") is True and bootstrap.get("VLX") is True:
        stage = "HEALTH OR RPC CHECK FAILED"
        detail = "Both chains are bootstrapped; inspect the health and RPC results above before serving requests."
    else:
        stage = "READINESS UNCONFIRMED"
        detail = "Some readiness checks are unavailable. Inspect the responses above and startup logs."
    print(f"\nStage: {stage}")
    print(detail)
    if vlx_missing and bootstrap.get("P") is not True:
        print("VLX is not registered yet; its RPC can return 404 before chain startup. This alone does not show snapshot corruption.")
    if not ready:
        print("Progress / ETA: unavailable from these API checks. A restored database may still need initialization and catch-up.")
        print("Next: sudo bash vlx-node.sh logs --tail 100")
        print("Compare progress logs and repeat status; if unchanged, inspect errors and peer connectivity. Do not reset or restore the database again based only on this status.")


def status(base):
    code, body = request(base, "/ext/health")
    health_code = code
    healthy = code == 200 and body.get("healthy") is True
    print(f"Health: {str(healthy).lower()} (HTTP {code})")
    checks = body.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    network = object_value(object_value(checks.get("network")).get("message"))
    print(f"Connected peers: {network.get('connectedPeers', 'unavailable')}")
    pcheck = object_value(checks.get("P"))
    percent = object_value(object_value(pcheck.get("message")).get("networking")).get("percentConnected")
    if isinstance(percent, (int, float)):
        print(f"P connected stake: {percent * 100:.2f}%")
    for label in ("P", "bootstrapped"):
        error = object_value(checks.get(label)).get("error")
        if error:
            print(f"{label}: {error}")
    if not checks and not healthy:
        print(error_text(code, body))
    bootstrapped = True
    bootstrap = {}
    vlx_missing = False
    for label, chain in (("P", "P"), ("VLX", BID)):
        code, result = request(base, "/ext/info", "info.isBootstrapped", {"chain": chain})
        value = object_value(result.get("result")).get("isBootstrapped")
        bootstrap[label] = value if code == 200 and isinstance(value, bool) else None
        if label == "VLX":
            vlx_missing = "there is no chain with alias/ID" in error_text(code, result)
        success = code == 200 and value is True
        bootstrapped = bootstrapped and success
        detail = str(value).lower() if code == 200 and isinstance(value, bool) else error_text(code, result)
        print(f"{label} bootstrap: {detail}")
    chain_ok = False
    height_ok = False
    for method in ("eth_chainId", "eth_blockNumber"):
        code, result = request(base, f"/ext/bc/{BID}/rpc", method)
        value = result.get("result")
        if code != 200 or not isinstance(value, str):
            print(f"{method}: {error_text(code, result)}")
            continue
        if method == "eth_chainId":
            chain_ok = value.lower() == "0x15f90"
            print(f"EVM Chain ID: {value} (expected 0x15f90 / 90000)")
        else:
            try:
                height = int(value, 16)
                height_ok = height >= 0
                print(f"VLX block height: {height} ({value})")
            except ValueError:
                print("VLX block height: invalid response")
    ready = healthy and bootstrapped and chain_ok and height_ok
    explain_stage(health_code, checks, network.get("connectedPeers"), bootstrap, vlx_missing, ready)
    print("Node ready." if ready else
          "Node not ready for RPC service (exit status 1).")
    return 0 if ready else 1


if __name__ == "__main__":
    restore_history(configured_data_dir())
    raise SystemExit(status(os.environ.get("RPC_URL", "http://127.0.0.1:9650")))
