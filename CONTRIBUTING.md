# Contributing

```bash
bash vlx-node.sh init
python3 -m unittest discover -s tests
sudo bash vlx-node.sh config
sudo bash vlx-node.sh build
```

Use the root `docker-compose.yml` together with `deploy/compose.rpc.yml` or `deploy/compose.validator.yml`. For version changes, update `versions.env`, the Dockerfile, `.env.example` and Compose defaults consistently, and use the VM from the same release.

Keep Bash scripts in LF format. Snapshot changes require regression checks for existing-data protection, checksum failures, unsafe paths and archive links. RPC changes must preserve rejection of Admin/debug methods and mixed batches containing prohibited methods. Use the acceptance checklist in `docs/quickstart.md` for each target operating system. Keep host-specific test results and operational details in your deployment records; summarize relevant validation without sensitive data in pull requests. Never commit live `.env` files, keys, tokens, operational address inventories or databases.

`python3 scripts/package-public.py` creates ZIP, TAR and TAR.GZ source packages with the same selected content. `versions.env` pins CI builds; local Compose reads the shell or `.env`, whose public template is `.env.example`. See [version sources](docs/configuration.md#which-version-file-is-used).
