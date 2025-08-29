from typing import List, Optional, Protocol

from summarizer.services.summaries.models.scene_summary import SceneSummary

from .models.insert_response import InsertResponse


class KnowledgeGraph(Protocol):
    """
    A knowledge graph indexes scenes to be later queried for precise information retrieval.
    """

    async def index_scenes(self, campaign_id: int, episode_id: int, scene_summaries: List[SceneSummary]) -> List[InsertResponse]:
        """
        Publish scene summaries to the knowledge graph.

        Args:
            campaign_id: The campaign identifier
            episode_id: The episode identifier  
            scene_summaries: List of scene summaries to publish

        Returns:
            List of insert responses from the knowledge graph
        """
        ...

    async def query(self, query: str, campaign_id: int, episode_id: Optional[int]) -> str:
        ...
