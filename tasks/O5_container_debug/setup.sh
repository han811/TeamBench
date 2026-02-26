#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$1"
REPORTS="$2"
RUN_ID="$3"
mkdir -p "$REPORTS"
mkdir -p "$WORKSPACE/submission"

# Snapshot the original Dockerfile for diff grading
cp "$WORKSPACE/Dockerfile" "$WORKSPACE/.Dockerfile.orig" 2>/dev/null || true
