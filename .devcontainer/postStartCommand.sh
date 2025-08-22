#!/usr/bin/env bash
set -ex

dapr uninstall && dapr init --runtime-version 1.15.10

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
    mcr.microsoft.com/dotnet/aspire-dashboard:9.4