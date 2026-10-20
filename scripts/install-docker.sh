#!/usr/bin/env bash
# Run explicitly with sudo on a new Ubuntu 22.04/24.04 or Rocky Linux 9 host.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run: sudo bash scripts/install-docker.sh' >&2; exit 1; }
source /etc/os-release
case "$ID:$VERSION_ID" in
  ubuntu:22.04|ubuntu:24.04)
    apt-get update
    apt-get install -y ca-certificates curl gnupg jq python3 git tar nginx
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin ;;
  rocky:9|rocky:9.*)
    dnf install -y dnf-plugins-core ca-certificates jq python3 git tar nginx
    command -v curl >/dev/null || dnf install -y curl
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin ;;
  *) echo "Supported: Ubuntu 22.04/24.04, Rocky Linux 9. Detected: $ID $VERSION_ID" >&2; exit 1;;
esac
systemctl enable --now docker
docker version
docker compose version
echo 'Docker installed. Review firewall, .env and keys before starting a node.'
