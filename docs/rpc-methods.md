# Public RPC methods

Request path: Nginx HTTPS 443 -> loopback gateway 9652 -> the VLX EVM RPC on Compose service `vlx-node:9650`.

The authoritative allowlist is `ALLOWED` in `scripts/rpc-gateway.py`:

- Queries: `eth_chainId`, `eth_blockNumber`, `eth_getBalance`, `eth_getCode`, `eth_getTransactionCount`.
- Blocks and transactions: `eth_getBlockByNumber`, `eth_getBlockByHash`, `eth_getTransactionByHash`, `eth_getTransactionReceipt`, `eth_getLogs`.
- Execution and fees: `eth_call`, `eth_estimateGas`, `eth_gasPrice`, `eth_maxPriorityFeePerGas`, `eth_feeHistory`.
- Submission: `eth_sendRawTransaction` (already signed transactions only).
- Metadata: `net_version`, `web3_clientVersion`.

Admin/debug/personal methods, other chain/P-Chain APIs and WebSocket endpoints are not exposed. Limits are 20 calls per JSON-RPC batch, a 1 MiB request body and a 16 MiB upstream response. A prohibited method rejects the entire batch with HTTP 403. Invalid JSON receives 400, an oversized request receives 413, and an upstream failure receives 502.

```bash
# Expected: a successful response containing 0x15f90.
curl -i https://YOUR_RPC_DOMAIN/rpc -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
# Expected: HTTP 403.
curl -i https://YOUR_RPC_DOMAIN/rpc -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"debug_traceTransaction","params":[]}'
# Expected: HTTP 404.
curl -i https://YOUR_RPC_DOMAIN/ext/admin
```

Historical state access, large `eth_getLogs` ranges and expensive `eth_call` workloads require separate capacity and quota planning. This lightweight gateway does not replace authentication or per-customer quota management. Load-test the service and confirm rate limits before expanding public access. An allowed method is not a guarantee that every historical query can be served by the underlying database.
