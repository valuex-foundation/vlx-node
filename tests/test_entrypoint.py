import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")


@unittest.skipUnless(BASH, "Bash required")
class EntrypointTests(unittest.TestCase):
    def run_entrypoint(self, role, keys, empty=False):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for key in keys:
                (folder / key).write_text("" if empty else "fixture")
            mock = folder / "mock-node.sh"
            mock.write_text('printf "%s\\n" "$@"\n', encoding="utf-8")
            script = ROOT.joinpath("docker/entrypoint.sh").read_text(encoding="utf-8")
            script = script.replace("/staking", folder.as_posix())
            script = script.replace("/opt/avalanchego/avalanchego", 'bash "$MOCK_NODE"')
            test_script = folder / "entrypoint.sh"
            with test_script.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(script)
            env = dict(os.environ, NODE_ROLE=role, MOCK_NODE=mock.as_posix(),
                       SUBNET_ID="2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv")
            return subprocess.run([BASH, test_script.as_posix()], env=env,
                                  text=True, capture_output=True)

    def test_new_rpc_uses_runtime_default_key_generation(self):
        result = self.run_entrypoint("rpc", [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--staking-tls-key-file=", result.stdout)
        self.assertIn("--api-admin-enabled=false", result.stdout)

    def test_validator_missing_keys_rejected(self):
        result = self.run_entrypoint("validator", [])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Validator requires", result.stderr)

    def test_partial_rpc_identity_rejected(self):
        result = self.run_entrypoint("rpc", ["staker.key"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Incomplete staking identity", result.stderr)

    def test_existing_validator_explicit_keys(self):
        result = self.run_entrypoint("validator", ["staker.key", "staker.crt", "signer.key"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--staking-tls-key-file=", result.stdout)
        self.assertIn("--staking-signer-key-file=", result.stdout)

    def test_empty_existing_rpc_keys_must_not_regenerate_identity(self):
        result = self.run_entrypoint("rpc", ["staker.key", "staker.crt", "signer.key"], empty=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid staking key", result.stderr)
