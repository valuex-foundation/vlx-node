# Ports, firewall and HTTPS

| Port | Purpose | Exposure policy |
|---|---|---|
| 443/TCP | Nginx RPC or a separate snapshot HTTPS service | Public service endpoint |
| 9650/TCP | AvalancheGo RPC, health and metrics | Loopback only; no direct public access |
| 9652/TCP | RPC method-filtering gateway | Loopback only; used by Nginx |
| 9651/TCP | Avalanche P2P | Allow as required for peer connectivity |
| 9090/TCP | Prometheus | Loopback; access through SSH tunneling/VPN |
| 3000/TCP | Grafana | Loopback; access through SSH tunneling/VPN |
| 9100/TCP | Node Exporter | Compose network only |
| 9101/TCP | VLX probe | Compose network only |
| 22/TCP | SSH | Fixed administrator IPs, or replace access with SSM |

The shared Compose configuration publishes 9651. RPC nodes also need peer connectivity. Apply upstream security groups/network ACLs as well as host policies. Docker-published ports may bypass UFW filtering; follow the [Docker firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/) and test exposure from an external host.

## Ubuntu

Keep the existing SSH session open and allow your administrator IP before changing access rules.

```bash
# Replace ADMIN_IP with the actual fixed address.
sudo ufw allow from ADMIN_IP to any port 22 proto tcp
sudo ufw allow 443/tcp
sudo ufw allow 9651/tcp
sudo ufw status verbose
# Enable UFW only after reviewing existing policy and verifying SSH access.
```

## Rocky Linux 9

Check the active zone with `firewall-cmd --get-active-zones`. These examples use the public zone:

```bash
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --zone=public --add-port=443/tcp
sudo firewall-cmd --permanent --zone=public --add-port=9651/tcp
# Restrict SSH using an administrator-IP rich rule or an SSM policy.
# Verify access before removing existing SSH rules.
sudo firewall-cmd --reload
sudo firewall-cmd --zone=public --list-all
```

Keep SELinux enabled. Bind mounts use `:Z`/`:z`. The Node Exporter host filesystem collector has a specific `label=disable` exception. If SELinux AVC denials block Nginx from reaching its loopback upstream, review the policy before applying `sudo setsebool -P httpd_can_network_connect 1`.

## Nginx

Prepare DNS and a valid TLS certificate using DNS-01 or your organization's certificate process. Nginx cannot start if certificates are missing from the configured paths.

1. Start the node and gateway using the RPC override.
2. Replace the domain and certificate paths in `deploy/nginx-rpc.conf.example`.
3. Install it as `/etc/nginx/conf.d/vlx-rpc.conf` and check for conflicting default servers.
4. Validate and apply the configuration:

```bash
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
curl -fsS https://YOUR_RPC_DOMAIN/rpc -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'
```

The expected result is `0x15f90`. Do not expose `/ext/admin`, `/ext/P`, `/ext/metrics` or WebSocket endpoints through this proxy. The Admin API is disabled at the node. The gateway checks request-body methods and rejects an entire batch if it includes any prohibited method.

The example limits are 10 requests/second per client IP, a burst of 20 and a 1 MiB request body. Confirm your production policy through load testing. Browser CORS is not provided by default; add only approved origins in Nginx if required.
