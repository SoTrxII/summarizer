import asyncio
import logging
from json import loads
from os import environ
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from dapr.ext.workflow import DaprWorkflowClient
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from summarizer.container import Container
from summarizer.services.speech_to_text import whisper
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.workflows import audio_to_summary
from summarizer.workflows.runtime import wfr

CURRENT_DIR = Path(__file__).parent
load_dotenv()


def setup_DI():
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
    container.wire(modules=[audio_to_summary])


def run_workflow_server():
    wfr.start()


async def main():
    setup_DI()
    run_workflow_server()


async def __azure_provider(foundry_endpoint: str, deployment_name: str) -> AzureChatCompletion:
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


async def summarize():
    foundry_endpoint = environ["AI_FOUNDRY_PROJECT_ENDPOINT"]
    deployment_name = environ["CHAT_DEPLOYMENT_NAME"]
    kernel = Kernel()

    kernel.add_service(await __azure_provider(
        foundry_endpoint=foundry_endpoint,
        deployment_name=deployment_name
    ))
    scenes_path = (
        CURRENT_DIR / "../../data/scenes/10m_sample2_scenes.json").resolve()
    with open(scenes_path, "r", encoding="utf-8") as f:
        scenes = loads(f.read())

    print(f"Loaded {len(scenes)} scenes from {scenes_path}")
    print("Summarizing scenes...")
    summaries = []
    for i, scene in enumerate(scenes):
        print(f"Scene {i} summary:")
        previous_summary = summaries[-1] if summaries else None
        scene_summary = await summarize_scene(kernel, scene, previous_summary)
        print(scene_summary)
        # with open(CURRENT_DIR / f"../../data/summaries/10m_sample2_scene_{i}_summary.json", "w", encoding="utf-8") as f:
        #     f.write(scene_summary.message.content)
        summaries.append(scene_summary.message.content)

    print("Aggregating session summary...")
    session_summary = await aggregate_session(kernel, summaries)
    with open(CURRENT_DIR / "../../data/summaries/10m_sample2_session_summary.json", "w", encoding="utf-8") as f:
        f.write(session_summary.message.content)
    print(session_summary)


def split_scenes():

    transcript_path = (
        CURRENT_DIR / "../../data/transcriptions/10m_sample2_diarized.json").resolve()
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    scenes = splitter.split_scenes(transcript)

    with open(CURRENT_DIR / "../../data/scenes/10m_sample2_scenes.json", "w", encoding="utf-8") as f:
        f.write(scenes)
    print(scenes)


if __name__ == "__main__":
    asyncio.run(main())
