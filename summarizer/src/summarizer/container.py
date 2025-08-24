from dependency_injector import containers, providers
from semantic_kernel import Kernel
from torch import cuda

from summarizer.services.speech_to_text import (
    AzureOpenAITranscriber,
    LocalWhisperTranscriber,
    SpeakersRecognition,
    SpeechToTextService,
)
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.services.transformers import SceneChunker
from summarizer.utils.azure_completion_provider import (
    azure_completion_provider,
    get_foundry_connection,
)


def setup_kernel(foundry_endpoint: str, deployment_name: str) -> Kernel:
    kernel = Kernel()
    az_openai = azure_completion_provider(foundry_endpoint, deployment_name)
    # Adjust if Semantic Kernel expects a specific method for registering
    kernel.add_service(az_openai)
    return kernel


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    config = providers.Configuration()

    # Detect device dynamically
    _default_device = "cuda" if cuda.is_available() and cuda.get_device_capability()[
        0] >= 7 else "cpu"
    device = providers.Callable(
        lambda inference_device: inference_device or Container._default_device,
        config.inference_device
    )

    # Transformers
    scene_chunker = providers.Factory(
        SceneChunker,
        device=device
    )

    # LLM Config -> Using Azure Foundry
    kernel = providers.Factory(
        setup_kernel,
        foundry_endpoint=config.foundry_endpoint,
        deployment_name=config.chat_deployment_name
    )

    foundry_con = providers.Singleton(
        get_foundry_connection,
        foundry_endpoint=config.foundry_endpoint
    )

    # Use Selector to choose between Azure and Local Whisper
    transcriber = providers.Selector(
        providers.Callable(
            lambda audio_deployment_name: "azure" if audio_deployment_name else "local",
            config.audio_deployment_name
        ),
        azure=providers.Factory(
            AzureOpenAITranscriber,
            endpoint=foundry_con.provided.target,
            api_key=foundry_con.provided.credentials.api_key,
            deployment_name=config.audio_deployment_name
        ),
        local=providers.Factory(
            LocalWhisperTranscriber,
            device=device
        )
    )

    sr = providers.Factory(
        SpeakersRecognition,
        hugging_face_token=config.hugging_face_token,
        device=device
    )

    speech_to_text = providers.Factory(
        SpeechToTextService,
        transcriber=transcriber,
        diarizer=sr
    )

    # Text summarizer using GPT 4.1
    summarizer = providers.Factory(
        Summarizer,
        kernel=kernel
    )
