"""
Dependency injection container for the summarizer application.
"""
from dependency_injector import containers, providers
from semantic_kernel import Kernel

from summarizer.services.speech_to_text import AzureSTT, WhisperX
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.azure_completion_provider import (
    azure_completion_provider,
    azure_speech_to_text_provider,
)


def setupKernel(foundry_endpoint: str, deployment_name: str) -> Kernel:
    kernel = Kernel()
    az_openai = azure_completion_provider(foundry_endpoint, deployment_name)
    az_stt = azure_speech_to_text_provider(foundry_endpoint, deployment_name)
    kernel.add_service(az_openai)
    kernel.add_service(az_stt)

    return kernel


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    config = providers.Configuration()

    # STT Model -> Using Whisper
    # speech_to_text = providers.Factory(
    #     WhisperX,
    #     hugging_face_token=config.hugging_face_token,
    #     device=config.inference_device or "cpu"
    # )

    # LLM Config -> Using Azure Foundry
    kernel = providers.Factory(
        setupKernel,
        config.foundry_endpoint,
        config.chat_deployment_name
    )

    # STT Model -> Using GPT4o transcribe
    speech_to_text = providers.Factory(AzureSTT, kernel=kernel)
    # Text to text model -> USing GPT 4.1
    summarizer = providers.Factory(Summarizer, kernel=kernel)
