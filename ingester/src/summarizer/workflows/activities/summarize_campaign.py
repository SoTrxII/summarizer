"""
Summarize campaign activity for the summarization workflow.
"""

import asyncio
import logging

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.workflow import SummarizeCampaignActivityInput
from summarizer.repositories.storage import SummaryRepository
from summarizer.services.summaries.models import EpisodeSummary
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def summarize_campaign(
    _: WorkflowActivityContext,
    campaign_input: SummarizeCampaignActivityInput,
    summarizer: Summarizer = Provide[Container.summarizer],
    summary_repo: SummaryRepository = Provide[Container.summary_repository]
) -> str:
    logging.info("Summarizing campaign...")

    episode = campaign_input["episode_summary"]
    campaign_id = campaign_input["campaign_id"]
    episode_id = campaign_input["episode_id"]

    async def run():
        episode_summary = EpisodeSummary(**episode)

        # Get all previous episodes
        episodes = []
        for previous_ep_id in range(1, episode_id):
            prev_summary = await summary_repo.get_episode_summary(campaign_id, previous_ep_id)
            if prev_summary:
                episodes.append(EpisodeSummary(**prev_summary))

        episodes.append(episode_summary)

        # Get previous campaign summary
        previous_campaign_summary = None
        campaign_summary = await summary_repo.get_campaign_summary(campaign_id)

        # Generate campaign summary
        campaign_summary = await summarizer.campaign(episodes, previous_campaign_summary)

        # Save campaign summary
        await summary_repo.save_campaign_summary(
            campaign_id,
            campaign_summary
        )

        return campaign_summary
    return asyncio.run(run())
