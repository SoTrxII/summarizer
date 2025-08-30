import logging
import os
from pathlib import Path
from typing import Generator

import pytest
import pytest_asyncio
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
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from summarizer.services.knowledge_graph import LightRAG
from summarizer.services.speech_to_text import (
    LocalWhisperTranscriber,
    SpeakersRecognition,
    SpeechToTextService,
)
from summarizer.services.speech_to_text.transcription import AzureOpenAITranscriber
from summarizer.services.summaries.models import SummaryArguments
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
from tests.utils.dapr import start_dapr_client

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
    return Summarizer(kernel, args=SummaryArguments(language=os.environ.get("LANGUAGE", "English")))


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
    return Summarizer(kernel, args=SummaryArguments(language=os.environ.get("LANGUAGE", "English")))


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

    return Summarizer(kernel, args=SummaryArguments(language=os.environ.get("LANGUAGE", "English")))


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


@pytest.fixture
def knowledge_graph():
    """Create a LightRAG service instance for testing."""
    return LightRAG(endpoint="http://localhost:9621", api_key="quackquack")


@pytest.fixture(scope="session")
def wf_client() -> Generator[DaprWorkflowClient, None, None]:
    """
    Start a Dapr sidecar for e2e tests, and return a workflow client
    """
    yield from start_dapr_client()
