#!/usr/bin/env python3
"""Manifest v1: uncompressed, immutable height-named snapshots."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

BID = "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR"
SID = "2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv"


def valid_filename(name, height):
    """Accept the original height name and the operator's timestamped chain name."""
    if not isinstance(name, str) or type(height) is not int or height < 0:
        return False
    return bool(re.fullmatch(
        rf"vlx-l1-(?:height-{height}|chain90000-height-{height}-[0-9]{{8}}-[0-9]{{6}})\.tar",
        name,
    ))


def manifest(cache):
    raw = (cache / "manifest.json").read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object")
    if "schemaVersion" not in data:
        sums = read_checksums(cache)
        if sums.get("manifest.json") != hashlib.sha256(raw).hexdigest():
            raise ValueError("Published manifest checksum mismatch")
        height = data.get("checkpointHeight")
        if isinstance(height, str) and re.fullmatch(r"0|[1-9][0-9]*", height):
            height = int(height)
        files = [name for name in sums if name != "manifest.json"]
        contents = data.get("contents")
        if (data.get("blockchainID") != BID or data.get("chainId") != "0x15f90"
                or type(height) is not int or height < 0
                or data.get("checkpointHeightHex") != hex(height)
                or data.get("stakingKeysIncluded") is not False
                or not isinstance(contents, list) or not all(isinstance(x, str) for x in contents)
                or "db" not in contents or not set(contents) <= {"db", "chainData", "config", "genesis", "plugins"}
                or len(files) != 1 or not valid_filename(files[0], height)):
            raise ValueError("Unsupported published manifest or chain identity")
        return {
            "metadataFormat": "published-checkpoint", "blockchainID": BID,
            "subnetID": None, "height": height, "type": "unknown", "compression": "none",
            "file": files[0], "sha256": sums[files[0]], "sizeBytes": None,
            "runtimeVersion": data.get("avalanchegoVersion"),
            "allowedExtraRoots": sorted(set(contents) - {"db", "chainData"}),
        }
    if (data.get("schemaVersion") != 1 or data.get("blockchainID") != BID
            or data.get("subnetID") != SID or data.get("evmChainID") != 90000
            or data.get("networkID") != 1 or data.get("compression") != "none"
            or data.get("type") not in ("unknown", "archive", "pruned")
            or type(data.get("height")) is not int or data["height"] < 0
            or type(data.get("sizeBytes")) is not int or data["sizeBytes"] <= 0
            or not re.fullmatch(r"[0-9a-f]{64}", data.get("sha256", ""))
            or not valid_filename(data.get("file"), data["height"])):
        raise ValueError("Invalid manifest, chain identity, size or checksum")
    return data


def read_checksums(cache):
    entries = {}
    for line in (cache / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] in entries:
            raise ValueError("Invalid or duplicate SHA256SUMS entry")
        entries[match[2]] = match[1]
    return entries


def verify(cache):
    data = manifest(cache)
    archive = cache / data["file"]
    sums = read_checksums(cache)
    allowed = {data["file"], "manifest.json"} if data.get("metadataFormat") == "published-checkpoint" else {data["file"]}
    if set(sums) != allowed or sums.get(data["file"]) != data["sha256"]:
        raise ValueError("SHA256SUMS does not match the manifest")
    if data["sizeBytes"] is not None and archive.stat().st_size != data["sizeBytes"]:
        raise ValueError("Snapshot size mismatch")
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != data["sha256"]:
        raise ValueError("Snapshot checksum mismatch")
    return archive


def empty_target(target):
    if target.is_symlink() or (target.exists() and (not target.is_dir() or any(target.iterdir()))):
        raise ValueError("Target must be an empty directory (existing DB/logs are never overwritten)")


def extract_safe(archive, target, allowed_extra_roots=None):
    target = Path(target)
    empty_target(target)
    with tarfile.open(archive, "r:") as source:
        members = source.getmembers()
        seen = set()
        total = 0
        extra = set(allowed_extra_roots or ())
        if not extra <= {"config", "genesis", "plugins"}:
            raise ValueError("Unexpected non-database archive roots")
        selected = []
        for member in members:
            name = PurePosixPath(member.name)
            if member.isdir() and member.name in (".", "./"):
                continue
            metadata_file = (
                allowed_extra_roots is not None
                and name.as_posix() in {"avalanchego-version.txt", "manifest.json"}
                and member.isfile() and 0 <= member.size <= 65536
            )
            if (name.is_absolute() or ".." in name.parts or "\\" in member.name
                    or not name.parts
                    or (name.parts[0] not in ({"db", "chainData"} | extra) and not metadata_file)
                    or not (member.isdir() or member.isfile())
                    or name.as_posix() in seen):
                raise ValueError(f"Unsafe or duplicate archive member: {member.name}")
            seen.add(name.as_posix())
            if name.parts[0] in {"db", "chainData"}:
                selected.append(member)
                total += member.size
        if not any(m.isfile() and PurePosixPath(m.name).parts[0] == "db" for m in selected):
            raise ValueError("Snapshot has no db files")
        target.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(target.parent).free < total + 1024 * 1024 * 1024:
            raise ValueError("Not enough free space (requires extracted size + 1 GiB)")
        stage = Path(tempfile.mkdtemp(prefix=".vlx-restore-", dir=target.parent))
        try:
            # Links/devices/path traversal rejected above; do not restore owners or modes.
            for member in selected:
                path = stage.joinpath(*PurePosixPath(member.name).parts)
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as src, path.open("xb") as dst:
                        shutil.copyfileobj(src, dst)
            empty_target(target)
            if target.exists():
                target.rmdir()  # Empty only; never recursive removal of user data.
            stage.rename(target)
        finally:
            if stage.exists():
                shutil.rmtree(stage)  # Only our newly allocated staging directory.


def independent_container_pids(target, containers):
    """Only whitelist processes after every running bind mount is disjoint."""
    for container in containers:
        for mount in container.get("Mounts", []):
            src = Path(mount["Source"]).resolve()
            if src == target or src in target.parents or target in src.parents:
                raise ValueError("A running container mounts the target; stop it first")
    pids = set()
    for container in containers:
        top = subprocess.check_output(
            ["docker", "top", container["Id"], "-eo", "pid"], text=True).splitlines()
        if not top or top[0].strip() != "PID":
            raise ValueError("Cannot verify running container process ownership")
        pids.update(int(row.strip()) for row in top[1:] if row.strip())
    return pids


def assert_stopped(target, allow_independent_containers=False):
    if os.name != "posix" or not Path("/proc").is_dir():
        raise ValueError("Restore must run on the Linux Docker host")
    if os.geteuid() != 0:
        raise ValueError("Run restore with sudo on the Docker host to inspect all node processes")
    endpoint = os.environ.get("DOCKER_HOST")
    if not endpoint or os.environ.get("DOCKER_CONTEXT"):
        context = json.loads(subprocess.check_output(["docker", "context", "inspect"], text=True))
        endpoint = context[0]["Endpoints"]["docker"]["Host"]
    if not endpoint.startswith("unix://"):
        raise ValueError("Restore requires a local Unix Docker socket, not a remote Docker context")
    ids = subprocess.check_output(["docker", "ps", "-q"], text=True).split()
    containers = json.loads(subprocess.check_output(
        ["docker", "inspect", *ids], text=True)) if ids else []
    # Mount checks apply in both modes. The default still rejects every live node.
    independent = independent_container_pids(target, containers)
    for proc in Path("/proc").glob("[0-9]*/comm"):
        try:
            if proc.read_text().strip() in ("avalanchego", "subnet-evm"):
                if allow_independent_containers and int(proc.parent.name) in independent:
                    continue
                raise ValueError("Local node process is running; stop it before restore")
        except FileNotFoundError:
            continue


def fetch(url, path):
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS downloads are accepted")
    # curl also enforces HTTPS redirects. Failed downloads remain .part, never trusted.
    subprocess.run(["curl", "--fail", "--location", "--proto", "=https",
                    "--proto-redir", "=https", "--retry", "3",
                    "--output", str(path) + ".part", url], check=True)
    Path(str(path) + ".part").replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["download", "verify", "restore"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--url", help="HTTPS release directory containing manifest.json and SHA256SUMS")
    parser.add_argument("--datadir", type=Path)
    parser.add_argument("--confirm-stopped", action="store_true")
    parser.add_argument("--allow-independent-containers", action="store_true",
                        help="Permit other Docker nodes only when their mounts do not overlap the target; native node processes remain forbidden")
    args = parser.parse_args()
    cache = args.cache.resolve()
    if args.command == "download":
        if not args.url:
            parser.error("download requires --url")
        cache.mkdir(parents=True, exist_ok=True)
        fetch(args.url.rstrip("/") + "/manifest.json", cache / "manifest.json")
        fetch(args.url.rstrip("/") + "/SHA256SUMS", cache / "SHA256SUMS")
        data = manifest(cache)
        fetch(args.url.rstrip("/") + "/" + data["file"], cache / data["file"])
        verify(cache)
        print("Downloaded and verified; no data directory was modified.")
    elif args.command == "verify":
        print(verify(cache))
    else:
        if not args.datadir or not args.confirm_stopped:
            parser.error("restore requires --datadir and --confirm-stopped")
        if args.datadir.is_symlink():
            raise ValueError("Symlink target is forbidden")
        target = args.datadir.resolve()
        if target == cache or cache in target.parents or target in cache.parents:
            raise ValueError("Cache and data directory must be separate")
        empty_target(target)
        assert_stopped(target, args.allow_independent_containers)
        archive = verify(cache)
        # Exclusive lock is shared with all restore invocations for this target.
        import fcntl
        target.parent.mkdir(parents=True, exist_ok=True)
        with (target.parent / f".{target.name}.restore.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert_stopped(target, args.allow_independent_containers)
            extract_safe(archive, target, manifest(cache).get("allowedExtraRoots"))
        print(f"Restored to {target}; configure DATA_DIR before starting.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        raise SystemExit(f"ERROR: {exc}")
