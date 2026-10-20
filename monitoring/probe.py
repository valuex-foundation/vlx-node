#!/usr/bin/env python3
"""Expose health, bootstrapped and RPC height without a Docker socket."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.request

BID = "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR"


def query(path, method=None, params=None):
    body = None if not method else json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method,
        "params": ([] if method.startswith("eth_") else {}) if params is None else params
    }).encode()
    req = urllib.request.Request("http://vlx-node:9650/" + path, body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.load(response)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        metrics = {}
        checks = {
            "vlx_health": lambda: int(query("ext/health")["healthy"]),
            "vlx_bootstrapped": lambda: int(query("ext/info", "info.isBootstrapped",
                                                 {"chain": BID})["result"]["isBootstrapped"]),
            "vlx_rpc_block_number": lambda: int(query("ext/bc/" + BID + "/rpc",
                                                     "eth_blockNumber")["result"], 16),
        }
        for name, check in checks.items():
            try:
                metrics[name] = check()
                metrics[name + "_probe_success"] = 1
            except (OSError, ValueError, KeyError, TypeError):
                metrics[name + "_probe_success"] = 0
        text = "".join(f"# TYPE {name} gauge\n{name} {value}\n"
                       for name, value in metrics.items()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(text)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9101), Handler).serve_forever()
