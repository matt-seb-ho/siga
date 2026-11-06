# Agent userland for siga-bench's bwrap sandbox (SIGA_ROOTFS).
# The runner binds this image's /usr and /etc read-only (and /opt/siga/venv for SIGA cells);
# nothing else from it is used.
# Build and unpack from the repository root (no container runtime is needed at run time):
#
#   docker build -t siga-agent benchmarks/siga-geos/sandbox
#   mkdir -p rootfs && docker export "$(docker create siga-agent)" | tar -x -C rootfs
#   export SIGA_ROOTFS=$PWD/rootfs
#
# Any equivalent tool (podman, enroot, a debootstrap chroot) works too.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git gnupg python3 python3-pip python3-venv libxml2-utils ripgrep \
    && rm -rf /var/lib/apt/lists/*
# Node.js 22 (the pi and Codex CLIs are bound in from the host; Claude Code lives in the image).
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
# uv, pinned.
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/0.12.17/install.sh | sh
# Claude Code, pinned to the version the SIGA paper used (2.1.119).
RUN npm install -g @anthropic-ai/claude-code@2.1.119
# Python environment for the SIGA MCP servers (R and X). In the sandbox there is no route to
# PyPI, so `uv run --script` cannot fetch dependencies; the siga agent starts the servers with
# /opt/siga/venv/bin/python instead.
COPY siga-mcp-requirements.txt /opt/siga/requirements.txt
RUN uv venv /opt/siga/venv --python /usr/bin/python3 \
    && uv pip install --python /opt/siga/venv/bin/python --no-cache -r /opt/siga/requirements.txt
RUN mkdir -p /workspace/inputs /geos_lib /plugins/siga
WORKDIR /workspace
