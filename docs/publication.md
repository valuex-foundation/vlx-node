# Source packaging and releases

The source packaging script selects public files for ZIP, TAR and TAR.GZ distribution. Live `.env` files, staking keys, databases, backups and blockchain snapshots are excluded. `.gitignore` does not remove files already tracked by Git or protect an archive of the entire workspace.

```bash
python3 scripts/package-public.py
unzip -l dist/vlx-node-public.zip
tar -tf dist/vlx-node-public.tar
tar -tzf dist/vlx-node-public.tar.gz
```

Packaging selects public directories/file extensions and an explicit set of root files. Under config, only Markdown and example files are included. It does not automatically detect credentials pasted into a new document, so review the archive contents before distribution. **Do not redistribute a ZIP of the original working directory.**

Extract a source archive into a clean directory and review its contents before publication. Run a content secret scan and the repository checks. CI checks tracked paths, tests, Compose configuration and image builds.

GitHub Releases should contain only manifest.json, SHA256SUMS, height, producing version, classification, restore-test results and HTTPS download links. Do not commit snapshot archives or attach them as Release assets. Keep private keys, tokens and live .env files out of the private operations repository as well; use SSM Parameter Store, Secrets Manager or another controlled secret store.

For an exchange or infrastructure-provider handoff, share the reviewed public source archives or published repository, network identity, RPC method documentation and the current deployment acceptance results. Resolve service endpoints, support contacts, confirmation policy and service commitments through the appropriate operational channel. Do not describe pending checks as completed certification.

## Distribution formats

One packaging command produces three equivalent source archives under `dist/`:

- `vlx-node-public.zip`
- `vlx-node-public.tar` (uncompressed)
- `vlx-node-public.tar.gz` (gzip-compressed)

All contain the same selected files under a single `vlx-node/` directory. TAR variants assign executable permissions to shell scripts and do not record local owner names. These are small source/configuration packages; they do not include blockchain snapshots or operational data.

To unpack on Linux, choose one format and use an empty working location:

```bash
mkdir vlx-source-unpack
cd vlx-source-unpack
# Replace the path with the downloaded source package.
tar -xzf /path/to/vlx-node-public.tar.gz
# For an uncompressed TAR instead: tar -xf /path/to/vlx-node-public.tar
cd vlx-node
```

Keep production usernames, absolute server paths and storage layouts out of public documents. Publish download URLs under `https://snapshot.valuex-foundation.com`; a public URL path need not match a server directory. Store backups independently from the source package.
