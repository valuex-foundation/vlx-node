# Network identity

Expected VLX chain registration returned by `platform.getBlockchains`:

```json
{
  "id": "zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR",
  "name": "vlxL1",
  "subnetID": "2o1i2YzX4FVfAzNHJYUnt4YFALuZNJGUvJS2nhx1zTTiGWUnZv",
  "vmID": "u9yY3bLZYo2z79xAfp3ib9WZNpw5GHCtz9RkT5xmdx4KuPGUC"
}
```

`NETWORK_ID=1` selects the AvalancheGo network. `90000` is the EVM Chain ID. They are separate identifiers and must not be substituted for each other. The Blockchain ID identifies the RPC path and chain configuration directory; the Subnet ID is passed to `--track-subnets`; the VM ID corresponds to the plugin executable name.

After P-Chain bootstrapping completes, verify the registration on your node:

```bash
BLOCKCHAIN_ID=zNXAbLSpaqfn3PTLi6ztbeomNtj4wsa7tBxSPyvXYEKstrtsR
curl -fsS http://127.0.0.1:9650/ext/P -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"platform.getBlockchains","params":{},"id":1}' |
  jq --arg BID "$BLOCKCHAIN_ID" '.result.blockchains[] | select(.id == $BID) | {id,name,subnetID,vmID}'
bash vlx-node.sh identity
bash vlx-node.sh status
```

`identity` fails if the expected record is missing or its Subnet ID or VM ID differs. `status` checks that the EVM Chain ID is `0x15f90`. Retain the output in the internal deployment record and stop deployment if any identifier differs. Also compare the live `.env`, systemd configuration and Compose arguments.
