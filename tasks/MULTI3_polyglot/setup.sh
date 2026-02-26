#!/usr/bin/env bash
# Setup script for MULTI3_polyglot.
# Called by the harness before the agent session begins.
# Args: $1=WORKSPACE $2=REPORTS $3=RUN_ID [$4=SEED]
set -euo pipefail

WORKSPACE="$1"
REPORTS="$2"
RUN_ID="$3"
SEED="${4:-0}"

# Create __init__.py stubs so Python finds the packages
for pkg in backend frontend shared tests; do
    touch "$WORKSPACE/$pkg/__init__.py"
done

echo "MULTI3_polyglot setup complete (seed=$SEED)"
