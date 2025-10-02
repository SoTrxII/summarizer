"""
Summarize scenes activity for the summarization workflow.
"""

import asyncio
import logging
from typing import List

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.workflow import SummarizeScenesActivityInput
from summarizer.repositories.storage import SummaryRepository
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def summarize_scenes(
    _: WorkflowActivityContext,
    input: SummarizeScenesActivityInput,
    summarizer: Summarizer = Provide[Container.summarizer],
    summary_repo: SummaryRepository = Provide[Container.summary_repository]
) -> List[dict]:
    logging.info("Summarizing scenes...")

    async def run():
        previous_summary = None
        summaries = []
        for scene in input["scenes"]:
            current = await summarizer.scene(scene, previous_summary=previous_summary)
            summaries.append(current.model_dump())
            previous_summary = current

        await summary_repo.save_scene_summaries(input["campaign_id"],  input["episode_id"], summaries)
        return summaries
    return asyncio.run(run())
