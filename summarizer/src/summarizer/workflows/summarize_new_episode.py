import asyncio
import logging
from json import dumps, loads
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
from summarizer.models.workflow import (
    AudioWorkflowInput,
    SummarizeCampaignActivityInput,
    SummarizeEpisodeActivityInput,
    WorkflowInput,
)
from summarizer.services.speech_to_text import SpeechToText
from summarizer.services.summaries.models.campaign_summary import CampaignSummary
from summarizer.services.summaries.models.episode_summary import EpisodeSummary
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
    input: AudioWorkflowInput,
    speech_to_text: SpeechToText = Provide[Container.speech_to_text]
) -> List[Sentence]:
    """
    Transcribe an audio file on a remote
    """
    # audio_file_path = audio_input["audio_file_path"]
    # campaign_id = audio_input["campaign_id"]
    # episode_id = audio_input["episode_id"]

    async def run():
        with DaprClient() as d, NamedTemporaryFile(suffix=".ogg") as tmp:
            binding_res = d.invoke_binding(
                "audio-store",
                "get",
                binding_metadata={"fileName": input["audio_file_path"]}
            )
            tmp.write(binding_res.data)
            sentences = await speech_to_text.transcribe(Path(tmp.name), diarize=True)
            binding_res = d.invoke_binding(
                "summary-store",
                "create",
                data=dumps(sentences),
                binding_metadata={
                    "fileName": f"{input['campaign_id']}/{input['episode_id']}/transcript.json"}
            )
            return sentences

    return asyncio.run(run())


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def split_into_scenes(_: WorkflowActivityContext, input: WorkflowInput, scene_chunker: SceneChunker = Provide[Container.scene_chunker]) -> List[Scene]:
    """
    Split transcribed text from object store into scenes
    """
    async def run():
        with DaprClient() as d:
            binding_res = d.invoke_binding(
                "summary-store",
                "get",
                binding_metadata={
                    "fileName": f"{input['campaign_id']}/{input['episode_id']}/transcript.json"
                }
            )
            sentences = loads(binding_res.data)
            scenes = scene_chunker.group_into_scenes(sentences)
            binding_res = d.invoke_binding(
                "summary-store",
                "create",
                data=dumps(scenes),
                binding_metadata={
                    "fileName": f"{input['campaign_id']}/{input['episode_id']}/scenes.json"
                }
            )
            return scenes

    return asyncio.run(run())


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
        # TODO : Publish scenes in knowledge-graph
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
    input: SummarizeEpisodeActivityInput,
    summarizer: Summarizer = Provide[Container.summarizer],
) -> dict:
    logging.info("Summarizing episode...")

    scenes = input["scenes_summaries"]
    campaign_id = input["campaign_id"]
    episode_id = input["episode_id"]

    async def run():
        scene_objects = [SceneSummary(**s) for s in scenes]
        # TODO : Should the episode have the campaign context instead of the previous episode context
        # # TODO: Whole campaign summary instead of episode summary?
        # TODO : Old episode from storage
        previous_episode = None
        for previous_ep_id in range(episode_id - 1, 0, -1):
            with DaprClient() as d:
                binding_res = d.invoke_binding(
                    "summary-store",
                    "get",
                    binding_metadata={
                        "fileName": f"{campaign_id}/{previous_ep_id}/episode.json"}
                )
                if binding_res.data:
                    previous_episode = EpisodeSummary(
                        **loads(binding_res.data))
                break

        # Incorporate previous episode summary into current episode
        episode_summary = await summarizer.episode(scene_objects, previous_episode)
        with DaprClient() as d:
            binding_res = d.invoke_binding(
                "summary-store",
                "create",
                data=episode_summary.model_dump_json(),
                binding_metadata={
                    "fileName": f"{campaign_id}/{episode_id}/episode.json"}
            )
        return episode_summary.model_dump()
    return asyncio.run(run())


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def summarize_campaign(
    _: WorkflowActivityContext,
    campaign_input: SummarizeCampaignActivityInput,
    summarizer: Summarizer = Provide[Container.summarizer],
) -> dict:
    logging.info("Summarizing campaign...")

    episode = campaign_input["episode"]
    campaign_id = campaign_input["campaign_id"]
    episode_id = campaign_input["episode_id"]

    async def run():
        episode_summary = EpisodeSummary(**episode)
        # TODO : Should the episode have the campaign context instead of the previous episode context
        # # TODO: Whole campaign summary instead of episode summary?
        # TODO : Old episode from storage
        episodes = []
        for previous_ep_id in range(0, episode_id - 1):
            with DaprClient() as d:
                binding_res = d.invoke_binding(
                    "summary-store",
                    "get",
                    binding_metadata={
                        "fileName": f"{campaign_id}/{previous_ep_id}/episode.json"}
                )
                if binding_res.data:
                    episodes.append(EpisodeSummary(
                        **loads(binding_res.data)))

        episodes.append(episode_summary)
        previous_campaign_summary = None
        with DaprClient() as d:
            binding_res = d.invoke_binding(
                "summary-store",
                "get",
                binding_metadata={
                    "fileName": f"{campaign_id}/campaign.json"}
            )
            if binding_res.data:
                previous_campaign_summary = CampaignSummary(
                    **loads(binding_res.data))
        campaign_summary = await summarizer.campaign(episodes, previous_campaign_summary)
        with DaprClient() as d:
            binding_res = d.invoke_binding(
                "summary-store",
                "create",
                data=campaign_summary.model_dump_json(),
                binding_metadata={
                    "fileName": f"{campaign_id}/{episode_id}/campaign.json"}
            )
        return campaign_summary.model_dump()
    return asyncio.run(run())


@wfr.workflow
def audio_to_summary(ctx: DaprWorkflowContext, input: AudioWorkflowInput):
    with tracer.start_as_current_span("audio_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting audio to summary workflow with payload: {input}")

            # Step 1: Transcribe
            logging.info("📝 Step 1: Starting transcription...")
            sentences: List[Sentence] = yield ctx.call_activity(
                transcribe_audio,
                input=input
            )
            logging.info(
                f"✅ Step 1 Complete. Transcribed {len(sentences)} sentences")

            # Step 2: Split into scenes
            logging.info("🎬 Step 2: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input={"campaign_id": input["campaign_id"], "episode_id": input["episode_id"]})
            logging.info(f"✅ Step 2 Complete. Split into {len(scenes)} scenes")

            # Step 3: Summarize scenes
            logging.info("📝 Step 3: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(summarize_scenes, input=scenes)
            logging.info(
                f"✅ Step 3 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 4: Summarize episode
            logging.info("📖 Step 4: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(
                summarize_episode,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"]
                }
            )
            logging.info("✅ Step 4 Complete. Episode summary generated")

            logging.info("🎉 Workflow completed successfully!")
            return episode_summary


@wfr.workflow
def transcript_to_summary(ctx: DaprWorkflowContext, input: WorkflowInput):
    with tracer.start_as_current_span("transcript_to_summary") as workflow_span:
        with trace.use_span(workflow_span, end_on_exit=False):
            logging.info(
                f"🎵 Starting transcript to summary workflow with campaign_id: {input['campaign_id']}, episode_id: {input['episode_id']}")

            # Step 1: Split into scenes
            logging.info("🎬 Step 1: Starting scene splitting...")
            scenes: List[Scene] = yield ctx.call_activity(split_into_scenes, input={"campaign_id": input["campaign_id"], "episode_id": input["episode_id"]})
            logging.info(f"✅ Step 1 Complete. Split into {len(scenes)} scenes")

            # Step 2: Summarize scenes
            logging.info("📝 Step 2: Starting scene summarization...")
            scenes_summaries = yield ctx.call_activity(summarize_scenes, input=scenes)
            logging.info(
                f"✅ Step 2 Complete. Generated {len(scenes_summaries)} scene summaries")

            # Step 3: Summarize episode
            logging.info("📖 Step 3: Starting episode summarization...")
            episode_summary = yield ctx.call_activity(
                summarize_episode,
                input={
                    "scenes_summaries": scenes_summaries,
                    "campaign_id": input["campaign_id"],
                    "episode_id": input["episode_id"]
                }
            )
            logging.info("✅ Step 3 Complete. Episode summary generated")

            logging.info("🎉 Workflow completed successfully!")
            return episode_summary
