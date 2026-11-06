# SIGA GEOS deck task image. Built from the GEOS source at a pinned upstream commit,
# with this task's reference deck, its variant siblings and its source tutorial removed
# (blocked_files.txt), and with no git history (git history contains every deck).
# Everything happens in ONE layer so the removed files never exist in any image layer.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git python3 libxml2-utils curl ripgrep \
    && rm -rf /var/lib/apt/lists/*
COPY blocked_files.txt /tmp/blocked_files.txt
RUN git init -q /geos_lib && cd /geos_lib \
    && git remote add origin https://github.com/GEOS-DEV/GEOS.git \
    && git fetch -q --depth 1 origin 498d8e33877a1c5539cc3f180c0991dd6189dea1 && git checkout -q FETCH_HEAD \
    && rm -rf .git .github .gitmodules \
    && xargs -a /tmp/blocked_files.txt -d '\n' rm -rf -- \
    && rm /tmp/blocked_files.txt \
    && chmod -R a-w /geos_lib
RUN mkdir -p /workspace/inputs /logs
WORKDIR /workspace
