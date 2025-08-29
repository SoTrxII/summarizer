from dependency_injector import containers, providers
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
from torch import cuda

from summarizer.config import AppConfig
from summarizer.repositories.dapr_storage import (
    DaprAudioRepository,
    DaprSummaryRepository,
)
from summarizer.services.knowledge_graph import LightRAG
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


def setup_azure_kernel(foundry_endpoint: str, deployment_name: str) -> Kernel:
    kernel = Kernel()
    az_openai = azure_completion_provider(foundry_endpoint, deployment_name)
    # Adjust if Semantic Kernel expects a specific method for registering
    kernel.add_service(az_openai)
    return kernel


def setup_ollama_kernel(endpoint: str, model_name: str) -> Kernel:
    kernel = Kernel()
    local_ollama = OllamaChatCompletion(ai_model_id=model_name, host=endpoint)
    kernel.add_service(local_ollama)
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

    # Storage repositories
    audio_repository = providers.Factory(
        DaprAudioRepository,
        binding_name=config.dapr_audio_store_name
    )
    summary_repository = providers.Factory(
        DaprSummaryRepository,
        binding_name=config.dapr_summary_store_name
    )

    # Azure foundry connection for Azure providers
    foundry_con = providers.Singleton(
        get_foundry_connection,
        foundry_endpoint=config.foundry_endpoint
    )

    ###################
    # Speech to text
    ###################

    transcriber = providers.Selector(
        config.audio_completion_provider,
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

    ###################
    # Chat completion
    ###################

    kernel = providers.Selector(
        config.chat_completion_provider,
        azure=providers.Factory(
            setup_azure_kernel,
            foundry_endpoint=config.foundry_endpoint,
            deployment_name=config.chat_deployment_name
        ),
        ollama=providers.Factory(
            setup_ollama_kernel,
            endpoint=config.ollama_endpoint,
            model_name=config.ollama_model_name
        ),
    )

    summarizer = providers.Factory(
        Summarizer,
        kernel=kernel
    )

    ###################
    # Knowledge Graph
    ###################

    knowledge_graph = providers.Factory(
        LightRAG,
        endpoint=config.lightrag_endpoint,
        api_key=config.lightrag_api_key
    )


def create_container(app_config: AppConfig) -> Container:
    """Create and configure the dependency injection container."""
    container = Container()
    # Configure the container with our typed configuration
    container.config.from_dict({
        'chat_completion_provider': app_config.chat_completion_provider,
        'audio_completion_provider': app_config.audio_completion_provider,
        'hugging_face_token': app_config.hugging_face_token,
        'foundry_endpoint': app_config.azure.foundry_endpoint,
        'chat_deployment_name': app_config.azure.chat_deployment_name,
        'audio_deployment_name': app_config.azure.audio_deployment_name,
        'ollama_endpoint': app_config.ollama.endpoint,
        'ollama_model_name': app_config.ollama.model_name,
        'inference_device': app_config.inference_device,
        'dapr_audio_store_name': app_config.dapr_audio_store_name,
        'dapr_summary_store_name': app_config.dapr_summary_store_name,
        'lightrag_endpoint': app_config.lightrag.endpoint,
        'lightrag_api_key': app_config.lightrag.api_key,
    })

    return container
