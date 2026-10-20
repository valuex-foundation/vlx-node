# Security

Keep private keys, live `.env` files and tokens out of both public and private Git repositories. If a credential is exposed, revoke or rotate it and review Git history; deleting the current file is not sufficient.

Report vulnerabilities through GitHub's private reporting channel when the repository Security tab offers **Report a vulnerability**. If that option is unavailable, ask the maintainers for a private reporting channel without including vulnerability details. Do not publish exploit details, credentials or private infrastructure information in public issues.

Before public deployment, verify that the Admin API is disabled, wildcard policies are absent, management ports are loopback-bound, HTTPS RPC methods are restricted, staking keys persist, snapshots are verified and test alerts reach the responsible operator. Configuration examples and passing local tests do not replace a security review of the deployed node.
