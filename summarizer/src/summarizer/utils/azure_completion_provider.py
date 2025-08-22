from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion


def azure_completion_provider(foundry_endpoint: str, deployment_name: str) -> AzureChatCompletion:
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
