import asyncio
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

from dapr.clients import DaprClient
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowActivityContext,
)
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence
from summarizer.services.speech_to_text import SpeechToText
from summarizer.services.summaries.models.episode_summary import EpisodeSummary
from summarizer.services.summaries.models.scene_summary import SceneSummary
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.services.transformers import group_into_scenes

from .runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
def transcribe_audio(
    _: WorkflowActivityContext,
    audio_file_path: str,
    speech_to_text: SpeechToText = Provide[Container.speech_to_text]
) -> List[Sentence]:
    """
    Transcribe an audio file on a remote 
    """
    with DaprClient() as d, NamedTemporaryFile(suffix=".ogg") as tmp:
        binding_res = d.invoke_binding(
            "object-store",
            "get",
            binding_metadata={"fileName": audio_file_path}
        )
        tmp.write(binding_res.data)
        sentences = speech_to_text.transcribe(Path(tmp.name), diarize=True)

    return sentences


@wfr.activity()  # pyright: ignore[reportCallIssue]
def split_into_scenes(_: WorkflowActivityContext, transcribed_text: List[Sentence]) -> List[Scene]:
    return group_into_scenes(transcribed_text)


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
def summarize_scenes(
    _: WorkflowActivityContext,
    scenes: List[Scene],
    summarizer: Summarizer = Provide[Container.summarizer],
) -> List[dict]:
    logging.info("Summarizing scenes...")

    async def run():
        previous_summary = None
        summaries = []
        for scene in scenes:
            current = await summarizer.scene(scene, previous_summary=previous_summary)
            summaries.append(current.model_dump())
            previous_summary = current
        return summaries

    return asyncio.run(run())


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
def summarize_episode(
    _: WorkflowActivityContext,
    scenes: List[dict],
    summarizer: Summarizer = Provide[Container.summarizer],
) -> EpisodeSummary:
    logging.info("Summarizing episode...")

    async def run():
        scene_objects = [SceneSummary(**s) for s in scenes]
        return await summarizer.episode(scene_objects)

    return asyncio.run(run())


@wfr.workflow
def audio_to_summary(ctx: DaprWorkflowContext, audio_payload_str: str):
    """
    Workflow to transcribe audio and summarize the content.
    """
    logging.info(
        f"🎵 Starting audio to summary workflow with payload: {audio_payload_str}")

    # Add detailed logging for debugging
    logging.info("📝 Step 1: Starting transcription...")
    sentences: List[Sentence] = yield ctx.call_activity(transcribe_audio, input=audio_payload_str)
    logging.info(f"✅ Step 1 Complete. Transcribed {len(sentences)} sentences")

    logging.info("🎬 Step 2: Starting scene splitting...")
    scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input=sentences)
    logging.info(f"✅ Step 2 Complete. Split into {len(scenes)} scenes")

    logging.info("📝 Step 3: Starting scene summarization...")
    scenes_summaries = yield ctx.call_activity(summarize_scenes, input=scenes)
    logging.info(
        f"✅ Step 3 Complete. Generated {len(scenes_summaries)} scene summaries")

    logging.info("📖 Step 4: Starting episode summarization...")
    episode_summary = yield ctx.call_activity(summarize_episode, input=scenes_summaries)
    logging.info(
        f"✅ Step 4 Complete. Episode summary generated: {type(episode_summary)}")

    logging.info(f"🎉 Workflow completed successfully!")
    return episode_summary
