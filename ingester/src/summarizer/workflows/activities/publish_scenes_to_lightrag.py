"""
Publish scenes to LightRAG activity for the summarization workflow.
"""

import asyncio
import logging
from typing import List

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.services.knowledge_graph import KnowledgeGraph
from summarizer.services.summaries.models import SceneSummary
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def publish_scenes_to_lightrag(
    _: WorkflowActivityContext,
    input: dict,
    knowledge_graph: KnowledgeGraph = Provide[Container.knowledge_graph],
) -> List[dict]:
    """
    Publish scene summaries to LightRAG knowledge graph.
    """
    logging.info("Publishing scenes to LightRAG...")

    scenes_summaries = input["scenes_summaries"]
    campaign_id = input["campaign_id"]
    episode_id = input["episode_id"]

    async def run():
        # Convert scene summaries back to SceneSummary objects
        scene_objects = [SceneSummary(**s) for s in scenes_summaries]

        # Publish to LightRAG
        responses = await knowledge_graph.index_scenes(campaign_id, episode_id, scene_objects)

        # Log results
        successful_publishes = sum(
            1 for r in responses if r.status == "success")
        total_scenes = len(responses)

        logging.info(
            f"Published {successful_publishes}/{total_scenes} scenes to LightRAG"
        )

        return [response.model_dump() for response in responses]

    return asyncio.run(run())
