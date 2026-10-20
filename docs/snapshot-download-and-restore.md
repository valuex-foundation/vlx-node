# Snapshot download and restoration

## What restoration does

Use the same public source package and Compose deployment as [sync from scratch](quickstart.md#option-a-sync-from-scratch). A snapshot supplies database files; it is not a separate node installer or Docker image.

The command path is:

```text
bash vlx-node.sh download|verify|restore ...
  -> scripts/vlx-node.sh
  -> python3 scripts/snapshot.py download|verify|restore ...
```

See the [CLI dispatcher](../scripts/vlx-node.sh) and [snapshot implementation](../scripts/snapshot.py). `main()` routes the command, `verify()` checks SHA-256, and `extract_safe()` inspects and extracts archive entries.

| Stage | What happens | Node / RPC ready? |
| --- | --- | --- |
| Download and checksum verification | Fetch metadata and TAR; compare file hashes | No |
| Restore-time checksum verification | Recheck cached TAR before changing the destination | No |
| Archive entry validation | Read the member list and reject unsafe paths, links, devices and unexpected roots | No; database extraction has not started |
| Database extraction | Copy only `db` and `chainData` into a temporary staging directory | No |
| Restore complete | Move the staging directory to `--datadir`; configure `DATA_DIR` | No; start the node separately |
| Node startup and synchronization | Open the restored DB and catch up with P-Chain and VLX | Not until readiness checks pass |
| RPC acceptance | Verify health, bootstrap, identity and current block data | Ready only if the checks pass |

The snapshot is an **uncompressed TAR**, so this is archive extraction, not gzip decompression. An archive scan reaching 100% does not mean extraction or node startup is complete. In `extract_safe()`, `source.getmembers()` and member validation run before files are copied.

“Included: db, chainData” describes snapshot data roots only. The deployment still needs a compatible AvalancheGo runtime, VM plugin, chain configuration and a persistent staking identity, supplied separately by the source package and host configuration.

The public CLI verifies checksums during both download and restore. Avoid adding a separate `verify` command unless you explicitly want another integrity check. The public CLI does not provide a checksum-bypass option.

## Release metadata and distribution format

The checkpoint release at height **53696** uses an **uncompressed `.tar`**. Read the producing runtime version from the release manifest and confirm compatibility before restoration. This release does not declare an archive/pruned classification; historical-state availability must be established separately. Renaming the file to `.tar.gz` does not compress it; do not extract it with gzip options.

The public download host is `https://snapshot.valuex-foundation.com`. Public URLs describe the download interface only; they do not disclose or depend on the publisher's filesystem layout. The examples below use the published timestamped release path. Use `--url` to select a different published release.

Exact file size and checksum must come from the actual archive. Neither a rounded disk-usage figure nor a file listing verifies the manifest schema, archive layout, producing runtime version or classification.

The tools accept the actual timestamped filename without renaming the archive. They also retain compatibility with `vlx-l1-height-53696.tar`. In both forms, the filename height must match the manifest; the timestamped form must specify chain `90000`. The snapshot is still an uncompressed TAR; source-package TAR.GZ support does not change snapshot compression support.

Publish an immutable release at the public HTTPS endpoint:

```text
https://snapshot.valuex-foundation.com/vlx-l1-chain90000-height-53696-20261020-122850/
  vlx-l1-chain90000-height-53696-20261020-122850.tar
  manifest.json
  SHA256SUMS
```

See the [manifest template](snapshot-manifest.json.example). `type: unknown` is valid, but a template with missing size/checksum values is rejected by the downloader. For the schemaVersion 1 format, `SHA256SUMS` must contain exactly one line: `64-character-lowercase-SHA256  vlx-l1-chain90000-height-53696-20261020-122850.tar`, with two spaces between hash and filename. Archive entries must be rooted under `db/` and, optionally, `chainData/`. Exclude private keys, logs, absolute paths, links and device files.

## Generated manifest compatibility

The downloader also accepts the generated format containing `network: "ValueX Chain"`, integer `chainId: 90000`, `height`, `format: "tar"`, `archive`, `archiveSizeBytes`, `archiveSha256`, and `contents: ["db", "chainData"]`. Its `SHA256SUMS` must include exactly the archive and `manifest.json`. Both metadata and archive hashes are checked; the archive size and filename height must match.

Timestamped names such as `vlx-archive-height-53696-20261020-154411.tar` are supported. The word `archive` in a filename does not prove historical-state availability. This format does not identify the Blockchain ID, Subnet ID or producing runtime. Confirm runtime compatibility with the publisher and run `identity` after bootstrap; missing identities are not inferred from the filename.

`Unsupported published manifest or chain identity` after metadata download means the metadata was rejected, not that the archive is missing. Use a source revision supporting the release format. Do not bypass checksum validation or rename JSON fields manually.

## Publisher procedure

The operator holding the actual file must verify the captured height, clean-shutdown status and database/runtime version. Use a timestamped filename that matches the release metadata. If the archive layout differs, inspect and repackage it in a separate staging area. Renaming an archive alone does not validate its internal layout.

Before generating metadata, inspect the files in a local staging directory. All local paths below are placeholders chosen by the publisher, not production server locations:

```bash
SNAPSHOT_DIR=/path/to/snapshot-staging
SNAPSHOT_FILE=vlx-l1-chain90000-height-53696-20261020-122850.tar
stat -c '%s' "$SNAPSHOT_DIR/$SNAPSHOT_FILE"
jq . "$SNAPSHOT_DIR/manifest.json"
cat "$SNAPSHOT_DIR/SHA256SUMS"
# Checks the existing metadata against this tool's schema and the actual bytes.
# Hashing a large archive can take substantial time and disk IO.
sudo bash vlx-node.sh verify --cache "$SNAPSHOT_DIR"
```

If the schema differs, preserve the original manifest and checksum file before adapting them. The generator below writes `manifest.json` and `SHA256SUMS` beside its input archive, replacing files with those names. Do not run it over the existing metadata without first saving copies and verifying the producing runtime version.

```bash
# Replace RUNTIME_VERSION with the actual producing AvalancheGo version.
python3 scripts/create-snapshot-manifest.py "$SNAPSHOT_DIR/$SNAPSHOT_FILE" \
  --height 53696 --runtime-version RUNTIME_VERSION --snapshot-type unknown
cd "$SNAPSHOT_DIR"
sha256sum -c SHA256SUMS
tar -tf vlx-l1-chain90000-height-53696-20261020-122850.tar | head
```

The metadata tool does not prove that the supplied height matches the database. Establish this using the pre-shutdown operational record and a separate restore test. Do not label an unverified snapshot as archive or pruned. Staking private keys must never be included.

Serve the archive and metadata through `snapshot.valuex-foundation.com`. The backing storage may be EC2 or R2; keep its internal paths out of public documentation. Upload and verify the archive first, then publish the metadata. Domain and release availability must be checked at publication time; this configuration does not deploy the download service. A GitHub Release should contain only the small metadata files, download links, height, producing version, classification and restore-test results. Use a new release path rather than overwriting a published artifact. Checksums verify integrity, not publisher identity independently; use a trusted HTTPS source and release record.

## Download and verify

```bash
sudo bash vlx-node.sh download --url https://snapshot.valuex-foundation.com/vlx-l1-chain90000-height-53696-20261020-122850 --cache /srv/vlx-snapshots/53696
# Optional additional verification; download already verifies the archive.
sudo bash vlx-node.sh verify --cache /srv/vlx-snapshots/53696
```

Downloading does not modify the database directory. The tool checks manifest identity, filename, format, size and hash, and requires matching checksum-file contents. Failed downloads remain as `.part` files; retries start the transfer again from the beginning. Retain the downloaded archive for verification or repeated restoration. Operators must review storage cleanup separately.

## Stop the node and restore

First stop any automatic start mechanisms, including systemd, cron or external orchestration. The tool cannot prevent an unrelated service from starting a node immediately after its checks. Run as root on the Linux host that owns the data and local Docker daemon. Remote Docker contexts are rejected.

```bash
sudo env VLX_ROLE=rpc VLX_MONITORING=1 bash vlx-node.sh stop
# Also stop any separately managed node service.
sudo docker ps
pgrep -a avalanchego || true
# Restore to a completely empty new location, not the existing ./data.
sudo bash vlx-node.sh restore --cache /srv/vlx-snapshots/53696 \
  --datadir /srv/vlx-data-restored --confirm-stopped
```

For validators, use `VLX_ROLE=validator` in the stop command. Restoration rejects nonempty destinations, symlink destinations, running containers mounting the target, and running local node processes. After checksum verification, it validates archive paths and file types, extracts into a staging directory on the same filesystem, and moves the result into place. It does not delete an existing database. The capacity check reserves the extracted size plus 1 GiB; this does not provide a database-growth allowance.

Set `DATA_DIR=/srv/vlx-data-restored` in `.env`. Check compatibility between the snapshot's producing version and the target runtime before starting. Keep `STAKING_DIR` pointed at the existing identity. An unknown snapshot classification does not guarantee archive RPC availability.

```bash
sudo bash vlx-node.sh start
sudo bash vlx-node.sh identity
sudo bash vlx-node.sh status
# For a validator start, use: sudo env VLX_ROLE=validator bash vlx-node.sh start
```

Verify the restored height, progress toward the network head, bootstrap completion and health. Preserve the previous data at a separate location until recovery has been accepted.

## Compatibility with the published checkpoint manifest

The timestamped release uses `chainId`, `checkpointHeight`, `checkpointHeightHex`,
`avalanchegoVersion`, `contents` and `stakingKeysIncluded`, rather than schemaVersion 1.
The helper also accepts this format. Its SHA256SUMS must contain exactly two entries:
the named TAR and `manifest.json`. The manifest checksum is verified before its fields
are used, and the complete archive checksum is verified before restoration.

This format does not include a Subnet ID, archive/pruned classification or exact byte size.
The helper does not invent those assertions: it checks the supplied Blockchain ID and
EVM Chain ID, treats snapshot type as unknown, and requires post-start P-Chain identity
verification. The file size is not independently checked against a manifest field in this
format; the full archive SHA256 still verifies its bytes.

The published contents list also names `config`, `plugins` and `genesis`. Restoration
validates archive entries but extracts **only db and chainData**. It does not install
archived executables, overwrite node settings or replace staking identity. Those extra
roots are accepted only when explicitly declared by this supported manifest format.
For this published format, root-level `avalanchego-version.txt` and `manifest.json` are also accepted as regular files up to 64 KiB each and skipped. Embedded metadata is not used as the verification source. Absolute paths, traversal, links and device files remain forbidden throughout the archive.

## Separate test nodes on one Docker host

For a deliberate comparison with another running Docker node, add
`--allow-independent-containers` to the restore command. This permits node processes
only when Docker identifies them as belonging to containers whose mounts are disjoint
from the restore target. Overlapping mounts and native host node processes still block
restoration. The target must still be empty and its own node must be stopped.

Use separate Compose projects, image tags, data directories, staking directories and
host ports for each experiment. Both image tags should use the same runtime version
so that the experiment compares synchronization methods rather than different clients.
Shared physical CPU, disk and network resources can affect timing; report this limitation.
