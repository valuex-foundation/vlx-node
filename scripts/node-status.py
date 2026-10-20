#!/usr/bin/env python3
"""Report bootstrap progress even when health returns HTTP 503."""
import json
import os
import urllib.error
import urllib.request

BID = "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR"


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


def status(base):
    code, body = request(base, "/ext/health")
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
    for label, chain in (("P", "P"), ("VLX", BID)):
        code, result = request(base, "/ext/info", "info.isBootstrapped", {"chain": chain})
        value = object_value(result.get("result")).get("isBootstrapped")
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
    print("Node ready." if ready else
          "Node not ready. If bootstrap is incomplete, inspect progress logs; do not reset the database.")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(status(os.environ.get("RPC_URL", "http://127.0.0.1:9650")))
