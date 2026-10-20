import importlib.util
import io
import hashlib
import json
import pathlib
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RestoreTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("snapshot", ROOT / "scripts/snapshot.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)

    def archive(self, name="db/mainnet/file", kind=tarfile.REGTYPE):
        path = self.base / "snapshot.tar"
        with tarfile.open(path, "w") as archive:
            item = tarfile.TarInfo(name)
            item.type = kind
            item.linkname = "../../escape"
            if kind == tarfile.REGTYPE:
                item.size = 4
                archive.addfile(item, io.BytesIO(b"test"))
            else:
                archive.addfile(item)
        return path

    def test_valid_restore(self):
        dest = self.base / "data"
        self.module.extract_safe(self.archive(), dest)
        self.assertEqual((dest / "db/mainnet/file").read_bytes(), b"test")

    def test_existing_data_untouched(self):
        dest = self.base / "data"
        dest.mkdir()
        (dest / "existing").write_text("keep")
        with self.assertRaises(ValueError):
            self.module.extract_safe(self.archive(), dest)
        self.assertEqual((dest / "existing").read_text(), "keep")

    def test_reject_traversal_absolute_and_unknown_roots(self):
        for name in ("../escape", "/tmp/escape", "db/../../escape", "config/staker.key"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.module.extract_safe(self.archive(name), self.base / "data")

    def test_reject_links_and_devices(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.module.extract_safe(self.archive(kind=kind), self.base / "data")

    def metadata(self):
        archive = self.archive()
        archive = archive.rename(self.base / "vlx-l1-height-53696.tar")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        data = {
            "schemaVersion": 1, "blockchainID": self.module.BID,
            "subnetID": self.module.SID, "networkID": 1, "evmChainID": 90000,
            "compression": "none", "type": "unknown", "height": 53696,
            "file": archive.name, "sha256": digest, "sizeBytes": archive.stat().st_size,
        }
        (self.base / "manifest.json").write_text(json.dumps(data))
        (self.base / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
        return archive, data

    def test_checksum_verifies_and_detects_corruption(self):
        archive, _ = self.metadata()
        self.assertEqual(self.module.verify(self.base), archive)
        contents = bytearray(archive.read_bytes())
        contents[512] ^= 1
        archive.write_bytes(contents)
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.module.verify(self.base)

    def test_manifest_wrong_chain_or_filename_rejected(self):
        _, data = self.metadata()
        for field, value in (("subnetID", "wrong"), ("evmChainID", 1),
                             ("file", "../outside.tar"), ("compression", "gzip"),
                             ("sha256", "pending"), ("sizeBytes", None)):
            modified = dict(data, **{field: value})
            (self.base / "manifest.json").write_text(json.dumps(modified))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.module.verify(self.base)

    def test_checksum_file_cannot_name_another_file(self):
        self.metadata()
        (self.base / "SHA256SUMS").write_text("0" * 64 + "  ../../secret\n")
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            self.module.verify(self.base)

    def test_operator_timestamped_snapshot_filename(self):
        archive, data = self.metadata()
        name = "vlx-l1-chain90000-height-53696-20261020-122850.tar"
        archive = archive.rename(self.base / name)
        data["file"] = name
        (self.base / "manifest.json").write_text(json.dumps(data))
        (self.base / "SHA256SUMS").write_text(f"{data['sha256']}  {name}\n")
        self.assertEqual(self.module.verify(self.base), archive)

    def test_timestamped_name_must_match_chain_and_height(self):
        _, data = self.metadata()
        for name in (
            "vlx-l1-chain1-height-53696-20261020-122850.tar",
            "vlx-l1-chain90000-height-53697-20261020-122850.tar",
            "../vlx-l1-chain90000-height-53696-20261020-122850.tar",
            "vlx-l1-chain90000-height-53696-20261020-122850.tar.gz",
        ):
            data["file"] = name
            (self.base / "manifest.json").write_text(json.dumps(data))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.module.verify(self.base)

    def test_published_legacy_manifest_and_two_checksums(self):
        archive = self.archive().rename(
            self.base / "vlx-l1-chain90000-height-53696-20261020-122850.tar")
        metadata = {
            "blockchainID": self.module.BID, "chainId": "0x15f90",
            "checkpointHeight": "53696", "checkpointHeightHex": "0xd1c0",
            "avalanchegoVersion": "avalanchego/1.15.0 [database=v1.4.5]",
            "contents": ["db", "chainData", "genesis", "plugins", "config"],
            "stakingKeysIncluded": False,
        }
        manifest = self.base / "manifest.json"
        manifest.write_text(json.dumps(metadata))
        (self.base / "SHA256SUMS").write_text(
            f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
            f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  manifest.json\n")
        self.assertEqual(self.module.verify(self.base), archive)
        normalized = self.module.manifest(self.base)
        self.assertEqual(normalized["height"], 53696)
        self.assertEqual(normalized["type"], "unknown")
        self.assertIsNone(normalized["subnetID"])
        manifest.write_text(json.dumps(dict(metadata, checkpointHeight=1)))
        with self.assertRaises(ValueError):
            self.module.verify(self.base)

    def test_legacy_restore_skips_non_database_content(self):
        archive = self.base / "legacy.tar"
        with tarfile.open(archive, "w") as tar:
            root = tarfile.TarInfo(".")
            root.type = tarfile.DIRTYPE
            tar.addfile(root)
            for name in ("./db/mainnet/file", "./chainData/state", "./plugins/vm",
                         "./config/config.json", "./genesis/genesis.json",
                         "avalanchego-version.txt", "manifest.json"):
                item = tarfile.TarInfo(name)
                item.size = 4
                tar.addfile(item, io.BytesIO(b"test"))
        target = self.base / "data"
        self.module.extract_safe(archive, target, allowed_extra_roots={"config", "genesis", "plugins"})
        self.assertEqual((target / "db/mainnet/file").read_bytes(), b"test")
        self.assertFalse((target / "plugins").exists())
        self.assertFalse((target / "config").exists())
        self.assertFalse((target / "genesis").exists())
        self.assertFalse((target / "avalanchego-version.txt").exists())
        self.assertFalse((target / "manifest.json").exists())

    def test_concurrent_restore_rejects_overlapping_container_mounts(self):
        target = (self.base / "data").resolve()
        for source in (target, target.parent, target / "db"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.module.independent_container_pids(target, [
                    {"Id": "node", "Mounts": [{"Source": str(source)}]}])

    def test_concurrent_restore_whitelists_only_disjoint_container_pids(self):
        target = (self.base / "snapshot-data").resolve()
        with patch.object(self.module.subprocess, "check_output",
                          return_value="PID\n123\n456\n"):
            pids = self.module.independent_container_pids(target, [
                {"Id": "sync-node", "Mounts": [{"Source": str(self.base / "sync-data")}]}])
        self.assertEqual(pids, {123, 456})


if __name__ == "__main__":
    unittest.main()
