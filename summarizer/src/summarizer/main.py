import asyncio
import logging
from os import environ
from typing import Never

import uvicorn
from dotenv import load_dotenv
from opentelemetry._logs import set_logger_provider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.attributes import service_attributes
from opentelemetry.trace import set_tracer_provider

from summarizer.api import app
from summarizer.container import Container
from summarizer.utils.telemetry import (
    setup_log_provider,
    setup_metrics_provider,
    setup_traces_provider,
)
from summarizer.workflows import summarize_new_episode
from summarizer.workflows.runtime import wfr

load_dotenv()


def setup_DI() -> None:
    """
    Create and inject dependencies into the dependency injection container.
    This will fail if any required environment variables are missing.
    """
    container = Container()

    (
        container
        .config
        .hugging_face_token
        .from_env("HUGGING_FACE_TOKEN", required=True)
    )
    (
        container
        .config
        .foundry_endpoint
        .from_env("AI_FOUNDRY_PROJECT_ENDPOINT", required=True)
    )
    (
        container
        .config
        .chat_deployment_name
        .from_env("AZURE_CHAT_DEPLOYMENT_NAME", required=True)
    )
    (
        container
        .config
        .audio_deployment_name
        .from_env("AZURE_AUDIO_DEPLOYMENT_NAME", required=False)
    )
    (
        container
        .config
        .inference_device
        .from_env("INFERENCE_DEVICE", required=False, default="cpu")
    )
    (
        container
        .config
        .dapr_audio_store_name
        .from_env("DAPR_AUDIO_STORE_NAME", required=False, default="audio-store")
    )
    (
        container
        .config
        .dapr_summary_store_name
        .from_env("DAPR_SUMMARY_STORE_NAME", required=False, default="summary-store")
    )
    container.wire(modules=[summarize_new_episode])


def setup_telemetry() -> None:
    otlp_endpoint = environ["OTLP_ENDPOINT"]
    resource = Resource.create({service_attributes.SERVICE_NAME: "summarizer"})
    set_tracer_provider(setup_traces_provider(resource, otlp_endpoint))
    set_logger_provider(setup_log_provider(resource, otlp_endpoint))
    set_meter_provider(setup_metrics_provider(resource, otlp_endpoint))


async def main() -> Never:
    """
    Runs the workflow server and HTTP API server concurrently.
    """
    setup_telemetry()
    setup_DI()

    # Start the workflow runtime
    wfr.start()

    # Get configuration for HTTP server
    host = environ.get("HTTP_HOST", "0.0.0.0")
    port = int(environ.get("HTTP_PORT", "8000"))

    logging.info(f"Starting HTTP API server on {host}:{port}")
    logging.info("Starting workflow runtime...")

    try:
        # Create uvicorn config
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )

        # Start uvicorn server
        server = uvicorn.Server(config)

        # Run the server (this will block)
        await server.serve()

        raise RuntimeError("Unreachable")

    except Exception as e:
        wfr.shutdown()
        logging.error(f"Error occurred: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
