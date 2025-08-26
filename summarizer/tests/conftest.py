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
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
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
async def azure_summarizer() -> Summarizer:
    """Summarizer using Azure provider only."""
    if not os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT") or not os.environ.get("AZURE_CHAT_DEPLOYMENT_NAME"):
        pytest.skip("Azure configuration not available")

    kernel = Kernel()
    azure_provider = azure_completion_provider(
        foundry_endpoint=os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_CHAT_DEPLOYMENT_NAME"]
    )
    kernel.add_service(azure_provider)
    return Summarizer(kernel)


@pytest_asyncio.fixture(scope="function")
async def ollama_summarizer() -> Summarizer:
    """Summarizer using Ollama provider only."""
    ollama_endpoint = os.environ.get(
        "OLLAMA_ENDPOINT", "http://localhost:11434")

    # Check if Ollama is available
    try:
        import requests
        response = requests.get(f"{ollama_endpoint}/api/tags", timeout=2)
        if response.status_code != 200:
            pytest.skip(f"Ollama not available at {ollama_endpoint}")
    except ImportError:
        pytest.skip("requests library not available for Ollama health check")
    except Exception:
        pytest.skip("Ollama not available or not responding")

    kernel = Kernel()
    from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
    ollama_provider = OllamaChatCompletion(
        ai_model_id=os.environ.get("OLLAMA_MODEL_NAME", "llama3.1"),
        host=ollama_endpoint
    )
    kernel.add_service(ollama_provider)
    return Summarizer(kernel)


@pytest_asyncio.fixture(params=["azure", "ollama"], scope="function")
async def summarizer(request: FixtureRequest) -> Summarizer:
    provider = request.param
    kernel = Kernel()

    if provider == "azure":
        # Check if Azure configuration is available
        if not os.environ.get("AI_FOUNDRY_PROJECT_ENDPOINT") or not os.environ.get("AZURE_CHAT_DEPLOYMENT_NAME"):
            pytest.skip(
                f"Azure configuration not available for {provider} provider")

        azure_provider = azure_completion_provider(
            foundry_endpoint=os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"],
            deployment_name=os.environ["AZURE_CHAT_DEPLOYMENT_NAME"]
        )
        kernel.add_service(azure_provider)
    elif provider == "ollama":
        # Check if Ollama is available (basic check)
        ollama_endpoint = os.environ.get(
            "OLLAMA_ENDPOINT", "http://localhost:11434")
        try:
            import requests
            response = requests.get(f"{ollama_endpoint}/api/tags", timeout=2)
            if response.status_code != 200:
                pytest.skip(f"Ollama not available at {ollama_endpoint}")
        except ImportError:
            pytest.skip(
                "requests library not available for Ollama health check")
        except Exception:
            pytest.skip("Ollama not available or not responding")

        ollama_provider = OllamaChatCompletion(
            ai_model_id=os.environ.get("OLLAMA_MODEL_NAME", "phi4"),
            host=ollama_endpoint
        )
        kernel.add_service(ollama_provider)
    else:
        raise ValueError(f"Unsupported chat provider: {provider}")

    return Summarizer(kernel)


@pytest_asyncio.fixture(scope="session")
async def azure_text_to_text_provider() -> AzureChatCompletion:
    return azure_completion_provider(
        foundry_endpoint=os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"],
        deployment_name=os.environ["AZURE_CHAT_DEPLOYMENT_NAME"]
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
    deployment_name = os.environ["AZURE_AUDIO_DEPLOYMENT_NAME"]
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

    app_id = "summarizer-testing"
    dapr_http_port = "3500"
    dapr_grpc_port = "50001"

    # Try to find daprd executable in common locations
    daprd_paths = [
        "/home/vscode/.dapr/bin/daprd",  # Dev container
        "/home/runner/.dapr/bin/daprd",  # GitHub Actions
        os.path.expanduser("~/.dapr/bin/daprd"),  # User home
        "daprd"  # System PATH
    ]

    daprd_path = None
    for path in daprd_paths:
        if path == "daprd":
            # Check if daprd is available in PATH
            try:
                subprocess.run(["which", "daprd"], check=True,
                               capture_output=True)
                daprd_path = path
                break
            except subprocess.CalledProcessError:
                continue
        elif os.path.exists(path):
            daprd_path = path
            break

    if not daprd_path:
        error_msg = "Could not find daprd executable. Please ensure Dapr is installed.\n"
        error_msg += "Searched locations:\n"
        for path in daprd_paths:
            exists = "✓" if (path == "daprd" and os.system(
                "which daprd >/dev/null 2>&1") == 0) or os.path.exists(path) else "✗"
            error_msg += f"  {exists} {path}\n"
        error_msg += "To install Dapr, run: curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | /bin/bash"
        raise RuntimeError(error_msg)

    cmd = [
        daprd_path,
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

    log_dir = Path(__file__).parent / "logs"
    # Create the logs directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)
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
            with open(log_dir / stdout, "r") as stdout_file, open(log_dir / stderr, "r") as stderr_file:
                print("=== Dapr stdout ===")
                print(stdout_file.read())
                print("=== Dapr stderr ===")
                print(stderr_file.read())
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
