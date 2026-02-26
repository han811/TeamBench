#!/usr/bin/env bash
# Setup for D5: Query Optimization
# Args: $1=WORKSPACE $2=REPORTS $3=RUN_ID
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"

mkdir -p "$WORKSPACE/tests" "$REPORTS"
