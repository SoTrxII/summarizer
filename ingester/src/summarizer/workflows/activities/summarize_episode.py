"""
Summarize episode activity for the summarization workflow.
"""

import asyncio
import logging

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.workflow import SummarizeEpisodeActivityInput
from summarizer.repositories.storage import SummaryRepository
from summarizer.services.summaries.models import EpisodeSummary, SceneSummary
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def summarize_episode(
    _: WorkflowActivityContext,
    input: SummarizeEpisodeActivityInput,
    summarizer: Summarizer = Provide[Container.summarizer],
    summary_repo: SummaryRepository = Provide[Container.summary_repository]
) -> dict:
    logging.info("Summarizing episode...")

    scenes = input["scenes_summaries"]
    campaign_id = input["campaign_id"]
    episode_id = input["episode_id"]
    is_one_shot = input["is_one_shot"]

    async def run():
        scene_objects = [SceneSummary(**s) for s in scenes]

        # Get previous episode (skip if this is a one-shot episode)
        previous_episode = None
        if not is_one_shot:
            for prev_id in range(episode_id - 1, 0, -1):
                prev_summary = await summary_repo.get_episode_summary(campaign_id, prev_id)
                if prev_summary:
                    previous_episode = EpisodeSummary(**prev_summary)
                    break

        # Generate episode summary
        episode_summary = await summarizer.episode(scene_objects, previous_episode)

        # Save episode summary
        await summary_repo.save_episode_summary(
            campaign_id,
            episode_id,
            episode_summary.model_dump()
        )

        return episode_summary.model_dump()
    return asyncio.run(run())
