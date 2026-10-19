#!/usr/bin/env bash
# Run the evidence tests in Docker (nothing installed on the host). Usage: bash tests/run-tests.sh
set -u
cd "$(dirname "$0")/.."
here=$(pwd -W 2>/dev/null || pwd)
MSYS_NO_PATHCONV=1 docker run --rm -v "$here:/lab:ro" -w /lab python:3.12-slim \
  sh -c "pip install -q pytest==8.3.4 2>/dev/null && python -m pytest -q -p no:cacheprovider tests"
