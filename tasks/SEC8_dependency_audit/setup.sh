#!/usr/bin/env bash
# Setup for SEC8_dependency_audit
# Workspace is pre-populated by the generator; nothing extra needed.
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"
mkdir -p "$REPORTS"
