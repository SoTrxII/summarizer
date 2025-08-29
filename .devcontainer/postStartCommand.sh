#!/usr/bin/env bash
set -ex
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LIGHTRAG_VERSION=1.4.6
DAPR_VERSION=1.15.11
ASPIRE_DASHBOARD_VERSION=9.4

# -- Dapr 
dapr uninstall && dapr init --runtime-version $DAPR_VERSION

# Start the Aspire Dashboard
# 18888 is the WEB UI port
# 4317 is the OTLP gRPC port
docker run --rm -it \
    -d \
    -p 18888:18888 \
    -p 4317:18889 \
    -e ASPIRE_DASHBOARD_UNSECURED_ALLOW_ANONYMOUS="true" \
    -e Dashboard:Frontend:AuthMode="Unsecured" \
    -e Dashboard:Otlp:AuthMode="Unsecured" \
    --name aspire-dashboard \
    mcr.microsoft.com/dotnet/aspire-dashboard:"$ASPIRE_DASHBOARD_VERSION"

bash "$SCRIPT_DIR/../rag/start-lightrag-server.sh" "$LIGHTRAG_VERSION"