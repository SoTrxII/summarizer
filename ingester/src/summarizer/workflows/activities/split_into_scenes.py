"""
Split into scenes activity for the summarization workflow.
"""

import asyncio
from typing import List

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.scene import Scene
from summarizer.models.workflow import WorkflowInput
from summarizer.repositories.storage import SummaryRepository
from summarizer.services.transformers import RuptureSceneChunker
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def split_into_scenes(
    _: WorkflowActivityContext,
    input: WorkflowInput,
    scene_chunker: RuptureSceneChunker = Provide[Container.scene_chunker],
    summary_repo: SummaryRepository = Provide[Container.summary_repository]
) -> List[Scene]:
    """
    Split transcribed text from object store into scenes
    """
    async def run():
        # Get transcript
        sentences = await summary_repo.get_transcript(
            input["campaign_id"],
            input["episode_id"]
        )

        if sentences is None:
            raise ValueError(
                f"Transcript not found for campaign {input['campaign_id']}, episode {input['episode_id']}")

        # Process scenes
        scenes = scene_chunker.group_into_scenes(sentences)

        # Save scenes
        await summary_repo.save_scenes(
            input["campaign_id"],
            input["episode_id"],
            scenes
        )

        return scenes

    return asyncio.run(run())
