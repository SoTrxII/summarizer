"""
Dependency injection container for the summarizer application.
"""
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from dapr.clients import DaprClient
from dependency_injector import containers, providers
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from summarizer.services.speech_to_text import WhisperX
from summarizer.services.summaries.summarizer import Summarizer


def __azure_provider(foundry_endpoint: str, deployment_name: str) -> AzureChatCompletion:
    """
        Authenticates with Azure IAFoundry and build an AzureChatCompletion using it
    """
    project_client = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=foundry_endpoint
    )

    connection = project_client.connections.get_default(
        connection_type=ConnectionType.AZURE_OPEN_AI, include_credentials=True
    )

    if connection.credentials.type != 'ApiKey':
        raise ValueError(
            f"Expected connection credentials type to be 'ApiKey', got {connection.credentials.type} instead."
        )

    return AzureChatCompletion(
        endpoint=connection.target,
        api_key=connection.credentials.api_key,  # type: ignore
        deployment_name=deployment_name,
        api_version='2025-01-01-preview',
    )


def setupKernel(foundry_endpoint: str, deployment_name: str) -> Kernel:
    kernel = Kernel()
    kernel.add_service(__azure_provider(foundry_endpoint, deployment_name))
    return kernel


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""

    # Configuration
    config = providers.Configuration()

    # STT Model -> Using Whisper
    speech_to_text = providers.Factory(
        WhisperX,
        hugging_face_token=config.hugging_face_token,
        device="cpu"  # Can be overridden
    )

    # LLM Config -> Using Azure Foundry
    kernel = providers.Factory(
        setupKernel,
        config.foundry_endpoint,
        config.chat_deployment_name
    )

    summarizer = providers.Factory(Summarizer, kernel=kernel)
