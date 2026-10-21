import importlib.util
import io
import json
from pathlib import Path
import threading
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]


class StatusTests(unittest.TestCase):
    def test_cancelled_status_returns_130_without_traceback(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "status", side_effect=KeyboardInterrupt), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.main([]), 130)
        self.assertIn("The node was not stopped", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_vlx_bootstrap_table_with_optional_snapshot_section(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        responses = [(503, {"healthy": False, "checks": {
            "network": {"message": {"connectedPeers": 578}},
            "P": {"message": {"networking": {"percentConnected": 0.9563}}}}}),
            (200, {"result": {"isBootstrapped": True}}),
            (200, {"result": {"isBootstrapped": False}}),
            (503, {"error": {"message": "API call rejected because chain is not done bootstrapping"}}),
            (503, {"error": {"message": "API call rejected because chain is not done bootstrapping"}})]
        with patch.object(module, "request", side_effect=responses), patch.object(module, "configured_data_dir", return_value=None), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.status("http://localhost", snapshots=True), 1)
        text = output.getvalue()
        self.assertIn("STAGE         VLX_BOOTSTRAPPING", text)
        self.assertRegex(text, r"P-Chain bootstrap\s+COMPLETE")
        self.assertRegex(text, r"VLX bootstrap\s+INCOMPLETE")
        self.assertIn("95.63%", text)
        self.assertLess(text.index("SNAPSHOT HISTORY"), text.index("ASSESSMENT"))
        self.assertIn("EXIT CODE     1", text)

    def test_snapshot_flag_is_optional_and_preserves_readiness_exit_code(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for args in ([], ["--snapshots"]):
            with self.subTest(args=args), patch.object(module, "status", return_value=1) as status, patch.object(module, "configured_data_dir", return_value=Path("data")) as directory, patch.object(module, "restore_history") as history:
                self.assertEqual(module.main(args), 1)
                status.assert_called_once_with(module.os.environ.get("RPC_URL", "http://127.0.0.1:9650"), snapshots=bool(args))
                history.assert_not_called()
                directory.assert_not_called()

    def test_restore_history_does_not_guess_for_older_restores(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with redirect_stdout(io.StringIO()) as output:
                module.restore_history(target)
            self.assertIn("NOT AVAILABLE", output.getvalue())
            (target / ".vlx-restore.json").write_text(json.dumps({
                "state": "restored", "height": 53696, "file": "snapshot.tar",
                "completedAt": "2026-10-21T00:00:00+00:00"}))
            with redirect_stdout(io.StringIO()) as output:
                module.restore_history(target)
            self.assertIn("53696", output.getvalue())
            self.assertIn("RESTORE COMPLETED", output.getvalue())
            self.assertIn("not the current P-Chain height", output.getvalue())

    def test_stage_explanations_keep_unready_exit_status(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = [
            (0, False, "not yet run", "INITIALIZING", "Health checks have not run"),
            (0, False, "not connected to enough stake", "WAITING_FOR_PEERS", "firewall"),
            (369, False, "not connected to enough stake", "P_CHAIN_BOOTSTRAPPING", "does not prove forward progress"),
            (369, True, None, "VLX_CHAIN_UNAVAILABLE", "SUBNET_ID"),
        ]
        for peers, p_ready, error, stage, hint in cases:
            health = {"healthy": False, "checks": {
                "network": {"message": {"connectedPeers": peers}},
                "P": {"error": error}}}
            responses = [(503, health), (200, {"result": {"isBootstrapped": p_ready}}),
                         (200, {"error": {"message": "there is no chain with alias/ID 'test'"}}),
                         (404, {}), (404, {})]
            with self.subTest(stage=stage), patch.object(module, "request", side_effect=responses), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(module.status("http://localhost"), 1)
            self.assertIn("STAGE         " + stage, output.getvalue())
            self.assertIn(hint, " ".join(output.getvalue().split()))
            self.assertIn("bash vlx-node.sh logs --since 5m --tail 100", output.getvalue())

    def test_ready_node_returns_success(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"healthy":true,"checks":{}}')

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                result = {"info.isBootstrapped": {"isBootstrapped": True},
                          "eth_chainId": "0x15f90", "eth_blockNumber": "0xd1c0"}[body["method"]]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"result": result}).encode())

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                code = module.status(f"http://127.0.0.1:{server.server_port}")
            self.assertEqual(code, 0)
            self.assertIn("53696 (0xd1c0)", output.getvalue())
            self.assertIn("READINESS     READY", output.getvalue())
            self.assertIn("ValueX | Node Diagnostics", output.getvalue())
            self.assertNotIn("SNAPSHOT HISTORY", output.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_bootstrap_503_still_reports_both_chains(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(503)
                self.end_headers()
                self.wfile.write(json.dumps({"healthy": False, "checks": {
                    "P": {"error": "not connected to enough stake",
                          "message": {"networking": {"percentConnected": 0.32}}},
                    "network": {"message": {"connectedPeers": 369}},
                    "bootstrapped": {"error": "subnets not bootstrapped"},
                }}).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append(body)
                if body["method"] == "info.isBootstrapped":
                    self.send_response(200)
                    content = {"result": {"isBootstrapped": False}}
                else:
                    self.send_response(503)
                    content = {"error": {"message": "chain is not done bootstrapping"}}
                self.end_headers()
                self.wfile.write(json.dumps(content).encode())

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                code = module.status(f"http://127.0.0.1:{server.server_port}")
            self.assertNotEqual(code, 0)
            text = output.getvalue()
            self.assertIn("32.00%", text)
            self.assertIn("369", text)
            self.assertRegex(text, r"P-Chain bootstrap\s+INCOMPLETE")
            self.assertRegex(text, r"VLX bootstrap\s+INCOMPLETE")
            self.assertIn("READINESS     NOT READY", text)
            self.assertEqual([x["params"]["chain"] for x in seen
                              if x["method"] == "info.isBootstrapped"], ["P", module.BID])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_null_fields_report_not_ready_without_crashing(self):
        spec = importlib.util.spec_from_file_location("node_status", ROOT / "scripts/node-status.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        responses = [(503, {"healthy": False, "checks": {
            "network": {"message": None}, "P": None, "bootstrapped": None}}),
            (200, {"result": None}), (200, {"result": None}),
            (200, {"result": None}), (200, {"result": None})]
        with patch.object(module, "request", side_effect=responses), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.status("http://localhost"), 1)
        self.assertRegex(output.getvalue(), r"VLX bootstrap\s+UNAVAILABLE")
        self.assertIn("READINESS     NOT READY", output.getvalue())
