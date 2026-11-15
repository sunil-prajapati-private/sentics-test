#!/usr/bin/env bash
set -u
for cmd in python3 node npm docker; do
  if command -v "$cmd" >/dev/null 2>&1; then echo "$cmd: $($cmd --version 2>&1 | head -1)"; else echo "$cmd: MISSING"; fi
done
command -v docker >/dev/null 2>&1 && docker compose version 2>&1 || true
