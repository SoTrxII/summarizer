import asyncio
import logging
from typing import Never

import uvicorn
from opentelemetry._logs import set_logger_provider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.attributes import service_attributes
from opentelemetry.trace import set_tracer_provider

from summarizer.api import app
from summarizer.config import get_config
from summarizer.container import create_container
from summarizer.utils.telemetry import (
    setup_log_provider,
    setup_metrics_provider,
    setup_traces_provider,
)
from summarizer.workflows import summarize_new_episode
from summarizer.workflows.runtime import wfr


def setup_DI() -> None:
    """
    Create and inject dependencies into the dependency injection container.
    This will fail if any required environment variables are missing.
    """
    # Load and validate configuration
    app_config = get_config()

    # Create container with validated configuration
    container = create_container(app_config)

    # Wire the container to workflows
    container.wire(modules=[summarize_new_episode])


def setup_telemetry() -> None:
    """Setup OpenTelemetry configuration."""
    config = get_config()

    if not config.otlp_endpoint:
        logging.warning(
            "OTLP_ENDPOINT is not set, telemetry will be disabled.")
        return

    resource = Resource.create({service_attributes.SERVICE_NAME: "summarizer"})
    set_tracer_provider(setup_traces_provider(resource, config.otlp_endpoint))
    set_logger_provider(setup_log_provider(resource, config.otlp_endpoint))
    set_meter_provider(setup_metrics_provider(resource, config.otlp_endpoint))


async def main() -> Never:
    """
    Runs the workflow server and HTTP API server concurrently.
    """
    setup_telemetry()
    setup_DI()

    # Start the workflow runtime
    wfr.start()

    # Get configuration for HTTP server
    config = get_config()

    logging.info(
        f"Starting HTTP API server on {config.http_host}:{config.http_port}")
    logging.info("Starting workflow runtime...")

    try:
        # Create uvicorn config
        uvicorn_config = uvicorn.Config(
            app=app,
            host=config.http_host,
            port=config.http_port,
            log_level="info",
            access_log=True
        )

        # Start uvicorn server
        server = uvicorn.Server(uvicorn_config)

        # Run the server (this will block)
        await server.serve()

        raise RuntimeError("Unreachable")

    except Exception as e:
        wfr.shutdown()
        logging.error(f"Error occurred: {e}")
        raise


def cli_main() -> None:
    """
    Synchronous entry point for the CLI script.
    """
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
