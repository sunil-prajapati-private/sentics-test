#!/usr/bin/env bash
set -euo pipefail
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r cloud/requirements.txt -r onprem/requirements.txt
