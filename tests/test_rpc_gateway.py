import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("gateway", Path(__file__).resolve().parents[1] / "scripts/rpc-gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def test_allowed(self):
        self.assertTrue(gateway.permitted({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": []}))

    def test_admin_debug_and_mixed_batch_rejected(self):
        for method in ("admin.startCPUProfiler", "debug_traceTransaction", "personal_unlockAccount"):
            self.assertFalse(gateway.permitted({"jsonrpc": "2.0", "method": method}))
            self.assertFalse(gateway.permitted([
                {"jsonrpc": "2.0", "method": "eth_chainId"},
                {"jsonrpc": "2.0", "method": method},
            ]))

    def test_invalid_payloads(self):
        for body in (None, [], {}, [1], {"jsonrpc": "2.0", "method": []}):
            self.assertFalse(gateway.permitted(body))
