import asyncio
import logging
from os import environ
from typing import Never

from dotenv import load_dotenv
from opentelemetry._logs import set_logger_provider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.attributes import service_attributes
from opentelemetry.trace import set_tracer_provider

from summarizer.container import Container
from summarizer.utils.telemetry import (
    setup_log_provider,
    setup_metrics_provider,
    setup_traces_provider,
)
from summarizer.workflows import audio_to_summary
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
        .from_env("CHAT_DEPLOYMENT_NAME", required=True)
    )
    (
        container
        .config
        .inference_device
        .from_env("INFERENCE_DEVICE", required=True, default="cpu")
    )
    container.wire(modules=[audio_to_summary])


def setup_telemetry() -> None:
    otlp_endpoint = environ["OTLP_ENDPOINT"]
    resource = Resource.create({service_attributes.SERVICE_NAME: "summarizer"})
    set_tracer_provider(setup_traces_provider(resource, otlp_endpoint))
    set_logger_provider(setup_log_provider(resource, otlp_endpoint))
    set_meter_provider(setup_metrics_provider(resource, otlp_endpoint))


async def main() -> Never:
    """
    Runs the workflow server and waits indefinitely.
    """
    setup_telemetry()
    setup_DI()
    wfr.start()

    try:
        await asyncio.Event().wait()
        raise RuntimeError("Unreachable")

    except Exception as e:
        wfr.shutdown()
        logging.error(f"Error occurred: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
