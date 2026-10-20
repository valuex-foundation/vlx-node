FROM rockylinux:9

# Base packages
RUN dnf update -y \
    && dnf install -y --allowerasing \
       curl wget jq tar gzip unzip ca-certificates \
       python3 \
    && dnf clean all

# Auto-detect architecture (amd64 / arm64)
ARG TARGETARCH
ARG AVALANCHEGO_VERSION=v1.15.0

# Consensus engine binary
RUN ARCH=$(case "${TARGETARCH:-$(uname -m)}" in \
      amd64|x86_64) echo "amd64" ;; \
      arm64|aarch64) echo "arm64" ;; \
      *) echo "Unsupported architecture" >&2; exit 1 ;; \
    esac) \
    && echo "Downloading AvalancheGo ${AVALANCHEGO_VERSION} for linux-${ARCH}" \
    && mkdir -p /opt/avalanchego \
    && wget -q "https://github.com/ava-labs/avalanchego/releases/download/${AVALANCHEGO_VERSION}/avalanchego-linux-${ARCH}-${AVALANCHEGO_VERSION}.tar.gz" \
       -O /tmp/avalanchego.tar.gz \
    && tar -xzf /tmp/avalanchego.tar.gz -C /opt/avalanchego --strip-components=1 \
    && rm /tmp/avalanchego.tar.gz \
    && chmod +x /opt/avalanchego/avalanchego

# EVM VM plugin — bundled with the AvalancheGo release since v1.15.0 (lockstep version,
# RPCChainVM protocol 46). Downloaded from the AvalancheGo release, NOT the old subnet-evm repo.
ARG VM_ID=srEXiWaHuhNyGwPUi444Tu47ZEDwxTWrbQiuD7FmgSAQ6X7Dy
ARG VM_ID2=u9yY3bLZYo2z79xAfp3ib9WZNpw5GHCtz9RkT5xmdx4KuPGUC
RUN set -eux; \
    ARCH=$(case "${TARGETARCH:-$(uname -m)}" in \
      amd64|x86_64) echo "amd64" ;; \
      arm64|aarch64) echo "arm64" ;; \
      *) echo "Unsupported architecture" >&2; exit 1 ;; \
    esac); \
    echo "Downloading subnet-evm plugin ${AVALANCHEGO_VERSION} (from AvalancheGo release) for linux-${ARCH}"; \
    mkdir -p /opt/avalanchego/plugins /tmp/sevm; \
    wget -q "https://github.com/ava-labs/avalanchego/releases/download/${AVALANCHEGO_VERSION}/subnet-evm-linux-${ARCH}-${AVALANCHEGO_VERSION}.tar.gz" \
       -O /tmp/subnet-evm.tar.gz; \
    tar -xzf /tmp/subnet-evm.tar.gz -C /tmp/sevm; \
    BIN="$(find /tmp/sevm -type f -name subnet-evm)"; \
    test -n "$BIN"; test -f "$BIN"; \
    mv "$BIN" /opt/avalanchego/plugins/${VM_ID}; \
    cp /opt/avalanchego/plugins/${VM_ID} /opt/avalanchego/plugins/${VM_ID2}; \
    chmod +x /opt/avalanchego/plugins/${VM_ID} /opt/avalanchego/plugins/${VM_ID2}; \
    rm -rf /tmp/subnet-evm.tar.gz /tmp/sevm

# Data / config directories
RUN mkdir -p /data/db /data/logs /config /staking /root/.avalanchego \
    && ln -s /staking /root/.avalanchego/staking

# Entrypoint (lives under docker/ in the repo)
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
