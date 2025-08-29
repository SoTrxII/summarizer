"""Configuration management for the summarizer application."""

from dataclasses import dataclass
from os import environ
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()

ChatProvider = Literal["azure", "ollama"]
AudioProvider = Literal["azure", "local"]


@dataclass
class ProviderConfig:
    """Base configuration for providers."""

    def validate(self) -> None:
        """Validate the configuration. Override in subclasses."""
        pass


@dataclass
class AzureConfig(ProviderConfig):
    """Azure provider configuration."""
    foundry_endpoint: Optional[str] = None
    chat_deployment_name: Optional[str] = None
    audio_deployment_name: Optional[str] = None

    def validate(self) -> None:
        """Validate Azure configuration."""
        if not self.foundry_endpoint:
            raise ValueError(
                "AI_FOUNDRY_PROJECT_ENDPOINT is required for Azure providers")


@dataclass
class OllamaConfig(ProviderConfig):
    """Ollama provider configuration."""
    endpoint: str = "http://localhost:11434"
    model_name: str = "llama3.1"

    def validate(self) -> None:
        """Validate Ollama configuration."""
        if not self.endpoint or not self.model_name:
            raise ValueError(
                "OLLAMA_ENDPOINT and OLLAMA_MODEL_NAME are required for Ollama")


@dataclass
class LightRAGConfig(ProviderConfig):
    """LightRAG provider configuration."""

    endpoint: str = "http://localhost:9621"
    api_key: Optional[str] = None

    def validate(self) -> None:
        """Validate LightRAG configuration."""
        if not self.endpoint:
            raise ValueError("LIGHTRAG_ENDPOINT is required for LightRAG")
        if not self.api_key:
            raise ValueError("LIGHTRAG_API_KEY is required for LightRAG")


@dataclass
class AppConfig:
    """Main application configuration."""

    # Provider selection
    chat_completion_provider: ChatProvider
    audio_completion_provider: AudioProvider

    # Required for all configurations
    hugging_face_token: str

    # Provider-specific configs
    azure: AzureConfig
    ollama: OllamaConfig
    lightrag: LightRAGConfig

    # Optional settings
    inference_device: str = "cpu"
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    dapr_audio_store_name: str = "audio-store"
    dapr_summary_store_name: str = "summary-store"
    otlp_endpoint: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""

        # Required settings
        hugging_face_token = environ.get("HUGGING_FACE_TOKEN")
        if not hugging_face_token:
            raise ValueError("HUGGING_FACE_TOKEN is required")

        # Provider selection
        chat_provider = environ.get("CHAT_COMPLETION_PROVIDER", "ollama")
        audio_provider = environ.get("AUDIO_COMPLETION_PROVIDER", "local")

        # Validate provider values
        if chat_provider not in ["azure", "ollama"]:
            raise ValueError(
                f"Invalid CHAT_COMPLETION_PROVIDER: '{chat_provider}'. Valid options: 'azure', 'ollama'")
        if audio_provider not in ["azure", "local"]:
            raise ValueError(
                f"Invalid AUDIO_COMPLETION_PROVIDER: '{audio_provider}'. Valid options: 'azure', 'local'")

        # Provider-specific configurations
        azure_config = AzureConfig(
            foundry_endpoint=environ.get("AI_FOUNDRY_PROJECT_ENDPOINT"),
            chat_deployment_name=environ.get("AZURE_CHAT_DEPLOYMENT_NAME"),
            audio_deployment_name=environ.get("AZURE_AUDIO_DEPLOYMENT_NAME")
        )

        ollama_config = OllamaConfig(
            endpoint=environ.get("OLLAMA_ENDPOINT", "http://localhost:11434"),
            model_name=environ.get("OLLAMA_MODEL_NAME", "phi4")
        )

        lightrag_config = LightRAGConfig(
            endpoint=environ.get("LIGHTRAG_ENDPOINT", "http://localhost:9621"),
            api_key=environ.get("LIGHTRAG_API_KEY")
        )

        return cls(
            chat_completion_provider=chat_provider,  # type: ignore
            audio_completion_provider=audio_provider,  # type: ignore
            hugging_face_token=hugging_face_token,
            azure=azure_config,
            ollama=ollama_config,
            lightrag=lightrag_config,
            inference_device=environ.get("INFERENCE_DEVICE", "cpu"),
            http_host=environ.get("HTTP_HOST", "0.0.0.0"),
            http_port=int(environ.get("HTTP_PORT", "8000")),
            dapr_audio_store_name=environ.get(
                "DAPR_AUDIO_STORE_NAME", "audio-store"),
            dapr_summary_store_name=environ.get(
                "DAPR_SUMMARY_STORE_NAME", "summary-store"),
            otlp_endpoint=environ.get("OTLP_ENDPOINT")
        )

    def validate(self) -> None:
        """Validate the entire configuration."""

        # Validate chat completion provider
        if self.chat_completion_provider == "azure":
            if not self.azure.foundry_endpoint or not self.azure.chat_deployment_name:
                raise ValueError(
                    "Azure chat completion provider requires: "
                    "AI_FOUNDRY_PROJECT_ENDPOINT and AZURE_CHAT_DEPLOYMENT_NAME"
                )
        elif self.chat_completion_provider == "ollama":
            self.ollama.validate()

        # Validate audio completion provider
        if self.audio_completion_provider == "azure":
            if not self.azure.foundry_endpoint or not self.azure.audio_deployment_name:
                raise ValueError(
                    "Azure audio completion provider requires: "
                    "AI_FOUNDRY_PROJECT_ENDPOINT and AZURE_AUDIO_DEPLOYMENT_NAME"
                )
        # Local audio provider needs no additional validation

    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()


def get_config() -> AppConfig:
    """Get the application configuration."""
    return AppConfig.from_env()
