#!/usr/bin/env bash
set -ex
LIGHTRAG_VERSION="${1:-1.4.6}"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p "$SCRIPT_DIR/data/rag_storage" "$SCRIPT_DIR/data/inputs"

docker run \
  -d \
  --rm \
  --name lightrag \
  -p ${PORT:-9621}:9621 \
  -v "$SCRIPT_DIR/data/rag_storage:/app/data/rag_storage" \
  -v "$SCRIPT_DIR/data/inputs:/app/data/inputs" \
  -v "$SCRIPT_DIR/.env:/app/.env" \
  --env-file "$SCRIPT_DIR/.env" \
  ghcr.io/hkuds/lightrag:"$LIGHTRAG_VERSION"
