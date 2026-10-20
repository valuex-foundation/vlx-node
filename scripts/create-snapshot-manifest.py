#!/usr/bin/env python3
"""Create metadata beside a stopped-node snapshot, after operator verification."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from snapshot import BID, SID, valid_filename

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
parser.add_argument("--height", type=int, required=True)
parser.add_argument("--runtime-version", required=True)
parser.add_argument("--snapshot-type", choices=["unknown", "archive", "pruned"], default="unknown")
args = parser.parse_args()
if not valid_filename(args.archive.name, args.height):
    parser.error("Expected vlx-l1-height-HEIGHT.tar or vlx-l1-chain90000-height-HEIGHT-YYYYMMDD-HHMMSS.tar")
with tarfile.open(args.archive, "r:") as archive:
    if not archive.getmembers():
        parser.error("Empty archive")
digest = hashlib.sha256()
with args.archive.open("rb") as source:
    for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
        digest.update(block)
data = {
    "schemaVersion": 1, "networkID": 1, "evmChainID": 90000,
    "blockchainID": BID, "subnetID": SID,
    "height": args.height, "type": args.snapshot_type, "compression": "none",
    "runtimeVersion": args.runtime_version,
    "file": args.archive.name, "sizeBytes": args.archive.stat().st_size,
    "sha256": digest.hexdigest(),
}
(args.archive.parent / "manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
(args.archive.parent / "SHA256SUMS").write_text(
    f"{digest.hexdigest()}  {args.archive.name}\n", encoding="ascii")
print("Metadata created. Verify archive layout and restore on a separate node before publishing.")
