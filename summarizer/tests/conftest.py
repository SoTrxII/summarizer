import http.client
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest
import pytest_asyncio
import requests
import torch
from _pytest.fixtures import FixtureRequest
from dapr.ext.workflow import DaprWorkflowClient
from dotenv import load_dotenv
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.attributes import service_attributes
from opentelemetry.trace import set_tracer_provider
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureAudioToText, AzureChatCompletion

from summarizer.services.speech_to_text import (
    LocalWhisperTranscriber,
    SpeakersRecognition,
    SpeechToTextService,
)
from summarizer.services.speech_to_text.transcription import AzureOpenAITranscriber
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.azure_completion_provider import (
    azure_completion_provider,
    azure_speech_to_text_provider,
    get_foundry_connection,
)
from summarizer.utils.telemetry import (
    setup_log_provider,
    setup_metrics_provider,
    setup_traces_provider,
)
from summarizer.workflows.runtime import wfr

load_dotenv()


ASPIRE_DASHBOARD = os.environ.get(
    "ASPIRE_DASHBOARD_URL", "http://localhost:4317")


@pytest.fixture(scope="function", autouse=True)
def exporter(request: FixtureRequest):
    test_name = request.node.name
    resource = Resource.create({service_attributes.SERVICE_NAME: test_name})
    set_tracer_provider(setup_traces_provider(resource, ASPIRE_DASHBOARD))
    set_logger_provider(setup_log_provider(resource, ASPIRE_DASHBOARD))
    set_meter_provider(setup_metrics_provider(resource, ASPIRE_DASHBOARD))

    # Enable automatic logging instrumentation for tests
    LoggingInstrumentor().instrument(set_logging_format=True)


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).parent.parent / "data"


@pytest_asyncio.fixture(scope="function")
async def summarizer(azure_text_to_text_provider: AzureChatCompletion) -> Summarizer:
    kernel = Kernel()
    kernel.add_service(azure_text_to_text_provider)
    return Summarizer(kernel)


@pytest_asyncio.fixture(scope="session")
async def azure_text_to_text_provider() -> AzureChatCompletion:
    return azure_completion_provider(
        foundry_endpoint=os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"],
        deployment_name=os.environ["CHAT_DEPLOYMENT_NAME"]
    )


@pytest_asyncio.fixture(params=["azure", "local"], scope="function")
async def speech_to_text(request: FixtureRequest, azure_transcribe: AzureOpenAITranscriber) -> SpeechToTextService:
    backend = request.param

    device = "cuda" if torch.cuda.is_available(
    ) and torch.cuda.get_device_capability()[0] >= 7 else "cpu"
    logging.info(f"Using device: {device}")
    sr = SpeakersRecognition(
        hugging_face_token=os.environ["HUGGING_FACE_TOKEN"],
        device=device
    )

    if backend == "azure":
        transcriber = azure_transcribe
    elif backend == "local":
        transcriber = LocalWhisperTranscriber(device)
    else:
        raise ValueError(f"Unsupported transcriber backend: {backend}")

    return SpeechToTextService(transcriber, sr)


@pytest_asyncio.fixture(scope="function")
async def azure_transcribe() -> AzureOpenAITranscriber:
    connection = get_foundry_connection(
        foundry_endpoint=os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"])
    deployment_name = os.environ["AUDIO_DEPLOYMENT_NAME"]
    key = connection.credentials.api_key  # type: ignore
    return AzureOpenAITranscriber(connection.target, key, deployment_name)


@pytest.fixture(scope="session")
def wf_client() -> Generator[DaprWorkflowClient, None, None]:
    """
    Start a Dapr sidecar for e2e tests, and return a workflow client
    """

    # Workspace and component paths
    workspace_root = Path(__file__).parent.parent.parent
    components_path = workspace_root / "components"

    app_id = "summarizertest"
    dapr_http_port = "3500"
    dapr_grpc_port = "50001"

    cmd = [
        "/home/vscode/.dapr/bin/daprd",
        "--app-id", app_id,
        "--dapr-http-port", dapr_http_port,
        "--dapr-grpc-port", dapr_grpc_port,
        "--placement-host-address", "0.0.0.0:50005",
        "--scheduler-host-address", "0.0.0.0:50006",
        "--resources-path", str(components_path.resolve()),
        "--config", str((components_path / "dapr-config.yaml").resolve()),
        "--log-level", "debug",  # Enable debug logs
    ]

    logging.info(f"Starting Dapr sidecar with: {' '.join(cmd)}")

    log_dir = workspace_root / "summarizer" / "tests" / "logs"
    stdout = "dapr_stdout.log"
    stderr = "dapr_stderr.log"

    with open(log_dir / stdout, "w") as stdout_file, open(log_dir / stderr, "w") as stderr_file:
        process = subprocess.Popen(
            cmd,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
            cwd=str(workspace_root)
        )

        if not _wait_for_dapr_sidecar(dapr_http_port):
            process.terminate()
            raise RuntimeError("Dapr sidecar failed to start")

        try:
            wfr.start()
            yield DaprWorkflowClient(host="0.0.0.0", port=dapr_grpc_port)
            wfr.shutdown()
        finally:
            # Cleanup Dapr process
            logging.info("Shutting down Dapr sidecar...")
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                logging.warning("Force killing Dapr sidecar process...")
                process.kill()


def _wait_for_dapr_sidecar(port, max_attempts=10, delay=1):
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"http://localhost:{port}/v1.0/healthz", timeout=2)
            if response.status_code == 204:
                logging.info(
                    f"Dapr sidecar is ready after {attempt + 1} attempts")
                return True
            else:
                logging.warning(
                    f"Health check failed: {response.status_code} - {response.text}")
        except (requests.RequestException, ConnectionError):
            pass
        logging.info(
            f"Dapr not ready (attempt {attempt + 1}/{max_attempts}), retrying...")
        time.sleep(delay)
    return False
