#!/usr/bin/env python3
"""Check tracked public paths without printing file contents."""
import subprocess
from pathlib import PurePosixPath

paths = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
bad = []
for path in filter(None, paths):
    p = PurePosixPath(path)
    if (p.parts[0] in ("data", "backup", "staking", "snapshots", "ops-private", "dist")
            or (p.name.startswith(".env") and p.name != ".env.example")
            or p.suffix in (".key", ".pem", ".crt", ".zip", ".tar", ".gz")
            or p.name in ("NODE_SNAPSHOT_ADDRESSES.md", "vlx_test.txt")
            or p.parts[0] == ".local-test"):
        bad.append(path)
if bad:
    raise SystemExit("Private/binary files tracked: " + ", ".join(bad))
print("Tracked public path policy passed (not a content secret scanner).")
