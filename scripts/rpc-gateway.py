#!/usr/bin/env python3
"""Small JSON-RPC method allowlist behind Nginx; no CORS or management endpoints."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import urllib.request
import urllib.error

UPSTREAM = "http://vlx-node:9650/ext/bc/zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR/rpc"
ALLOWED = frozenset((
    "eth_chainId", "eth_blockNumber", "eth_getBalance", "eth_getCode",
    "eth_getTransactionCount", "eth_getBlockByNumber", "eth_getBlockByHash",
    "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_call",
    "eth_estimateGas", "eth_gasPrice", "eth_maxPriorityFeePerGas",
    "eth_feeHistory", "eth_getLogs", "eth_sendRawTransaction",
    "net_version", "web3_clientVersion",
))


def permitted(body):
    calls = body if isinstance(body, list) else [body]
    return (1 <= len(calls) <= 20 and all(
        isinstance(call, dict) and call.get("jsonrpc") == "2.0"
        and isinstance(call.get("method"), str) and call["method"] in ALLOWED
        and isinstance(call.get("params", []), (list, dict))
        for call in calls))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/rpc":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(size)
            if not permitted(json.loads(body)):
                self.send_error(403, "RPC method is not permitted")
                return
            request = urllib.request.Request(UPSTREAM, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=25) as response:
                content = response.read(16 * 1024 * 1024 + 1)
                if len(content) > 16 * 1024 * 1024:
                    self.send_error(502)
                    return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (ValueError, UnicodeError):
            self.send_error(400)
        except (OSError, urllib.error.URLError):
            self.send_error(502)

    def setup(self):
        super().setup()
        self.connection.settimeout(30)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9652), Handler).serve_forever()
