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
from opentelemetry import trace

from summarizer.container import Container
from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence
from summarizer.services.speech_to_text import SpeechToText
from summarizer.services.summaries.models.scene_summary import SceneSummary
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.services.transformers import SceneChunker
from summarizer.utils.telemetry import span

from .runtime import wfr

# Get a tracer for this module
tracer = trace.get_tracer(__name__)


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def transcribe_audio(
    _: WorkflowActivityContext,
    audio_file_path: str,
    speech_to_text: SpeechToText = Provide[Container.speech_to_text]
) -> List[Sentence]:
    """
    Transcribe an audio file on a remote
    """

    async def run():
        with DaprClient() as d, NamedTemporaryFile(suffix=".ogg") as tmp:
            binding_res = d.invoke_binding(
                "object-store",
                "get",
                binding_metadata={"fileName": audio_file_path}
            )
            tmp.write(binding_res.data)
            sentences = await speech_to_text.transcribe(Path(tmp.name), diarize=True)
            return sentences

    return asyncio.run(run())


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def split_into_scenes(_: WorkflowActivityContext, transcribed_text: List[Sentence], scene_chunker: SceneChunker = Provide[Container.scene_chunker]) -> List[Scene]:
    return scene_chunker.group_into_scenes(transcribed_text)


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
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
@span
def summarize_episode(
    _: WorkflowActivityContext,
    scenes: List[dict],
    summarizer: Summarizer = Provide[Container.summarizer],
) -> dict:
    logging.info("Summarizing episode...")

    async def run():
        scene_objects = [SceneSummary(**s) for s in scenes]
        episode_summary = await summarizer.episode(scene_objects)
        with DaprClient() as d:
            binding_res = d.invoke_binding(
                "object-store",
                "create",
                data=episode_summary.model_dump_json(),
                binding_metadata={
                    "fileName": f"episode_summary.json"}
            )
        return episode_summary.model_dump()
    return asyncio.run(run())


@wfr.workflow
def audio_to_summary(ctx: DaprWorkflowContext, audio_payload_str: str):
    with tracer.start_as_current_span("audio_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting audio to summary workflow with payload: {audio_payload_str}")

            # Step 1: Transcribe
            logging.info("📝 Step 1: Starting transcription...")
            sentences: List[Sentence] = yield ctx.call_activity(transcribe_audio, input=audio_payload_str)
            logging.info(
                f"✅ Step 1 Complete. Transcribed {len(sentences)} sentences")

            # Step 2: Split into scenes
            logging.info("🎬 Step 2: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input=sentences)
            logging.info(f"✅ Step 2 Complete. Split into {len(scenes)} scenes")

            # Step 3: Summarize scenes
            logging.info("📝 Step 3: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(summarize_scenes, input=scenes)
            logging.info(
                f"✅ Step 3 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 4: Summarize episode
            logging.info("📖 Step 4: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(summarize_episode, input=scenes_summaries)
            logging.info(f"✅ Step 4 Complete. Episode summary generated")

            logging.info("🎉 Workflow completed successfully!")
            return episode_summary


@wfr.workflow
def transcript_to_summary(ctx: DaprWorkflowContext, sentences: List[Sentence]):
    with tracer.start_as_current_span("transcript_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting transcript to summary workflow with number of sentences: {len(sentences)}")

            # Step 1: Split into scenes
            logging.info("🎬 Step 1: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input=sentences)
            logging.info(f"✅ Step 1 Complete. Split into {len(scenes)} scenes")

            # Step 2: Summarize scenes
            logging.info("📝 Step 2: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(summarize_scenes, input=scenes)
            logging.info(
                f"✅ Step 2 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 3: Summarize episode
            logging.info("📖 Step 3: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(summarize_episode, input=scenes_summaries)
            logging.info(f"✅ Step 3 Complete. Episode summary generated")

            logging.info("🎉 Workflow completed successfully!")
            return episode_summary
