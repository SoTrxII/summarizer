"""LightRAG publisher service for publishing scene summaries to knowledge graph."""

import logging
from typing import List, Optional

import httpx

from summarizer.services.knowledge_graph.models.insert_response import InsertResponse
from summarizer.services.summaries.models.scene_summary import SceneSummary

from .models import LrInsertRequest, LrInsertResponse, LrQueryRequest, LrQueryResponse


class LightRAG:
    """Service for publishing summaries to LightRAG knowledge graph."""

    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        """
        Initialize the LightRAG publisher service.

        Args:
            endpoint: LightRAG server endpoint (e.g., http://localhost:9621)
            api_key: Optional API key for authentication
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    async def index_scenes(
        self,
        campaign_id: int,
        episode_id: int,
        scene_summaries: List[SceneSummary]
    ) -> List[InsertResponse]:

        responses: List[InsertResponse] = []

        for i, scene_summary in enumerate(scene_summaries):
            text_content = self._format_scene_summary_text(
                campaign_id, episode_id, i, scene_summary
            )

            res = await self._insert_document(LrInsertRequest(
                text=text_content,
                file_source=f"campaign_{campaign_id}_episode_{episode_id}_scene_{i + 1}"
            ))

            if res.status == "failure":
                self.logger.error(
                    f"Failed to insert scene {i + 1} for campaign {campaign_id}, episode {episode_id}: {res.message}")

            responses.append(InsertResponse(**res.model_dump()))

        return responses

    async def query(self, query: str, campaign_id: int, episode_id: Optional[int]) -> str:
        query_fmt = self._build_tags(campaign_id, episode_id)
        query_fmt.append(f"Query: {query}")

        res = await self._query_lightrag("\n".join(query_fmt))

        return res.response

    def _build_tags(self, campaign_id: int, episode_id: Optional[int] = None, scene_index: Optional[int] = None) -> List[str]:
        tags = [f"[Campaign: {campaign_id}]"]
        if episode_id is not None:
            tags.append(f"[Episode: {episode_id}]")
        if scene_index is not None:
            tags.append(f"[Scene: {scene_index + 1}]")
        return tags

    def _format_scene_summary_text(
        self,
        campaign_id: int,
        episode_id: int,
        scene_index: int,
        scene_summary: SceneSummary
    ) -> str:
        """
        Format a scene summary into a structured text document for LightRAG.

        Args:
            campaign_id: The campaign identifier
            episode_id: The episode identifier
            scene_index: The scene index within the episode
            scene_summary: The scene summary to format

        Returns:
            Formatted text document
        """
        # Header: structured, machine-parsable
        text_parts = self._build_tags(campaign_id, episode_id, scene_index)
        text_parts.append(
            f"[Timestamp: {scene_summary.timestamps.start:.1f}s - {scene_summary.timestamps.end:.1f}s]")

        # GM content
        text_parts.append("GM Content:")
        text_parts.append(scene_summary.gm_content)
        text_parts.append("")

        # Player actions
        if scene_summary.player_actions:
            text_parts.append("Player Actions:")
            for action in scene_summary.player_actions:
                mode_text = f" ({action.mode})" if action.mode != "in_character" else ""
                text_parts.append(
                    f"- {action.speaker}{mode_text}: {action.content}")
            text_parts.append("")

        # Items and clues
        if scene_summary.items_and_clues:
            text_parts.append("Items and Clues:")
            for item in scene_summary.items_and_clues:
                item_text = f"- {item.name}"
                if item.description:
                    item_text += f": {item.description}"
                if item.significance:
                    item_text += f" (Significance: {item.significance})"
                text_parts.append(item_text)
            text_parts.append("")

        # Open threads
        if scene_summary.open_threads:
            text_parts.append("Open Threads:")
            for thread in scene_summary.open_threads:
                thread_text = f"- {thread.description}"
                if thread.priority:
                    thread_text += f" (Priority: {thread.priority})"
                if thread.related_characters:
                    thread_text += f" [Characters: {', '.join(thread.related_characters)}]"
                text_parts.append(thread_text)
            text_parts.append("")

        # Footer: optional redundant machine-readable tags for parsing
        text_parts.append(
            f"__CAMPAIGN__{campaign_id}__EPISODE__{episode_id}__SCENE__{scene_index + 1}__")

        return "\n".join(text_parts)

    async def _query_lightrag(
        self,
        query: str,
        mode: str = "mix",
        only_need_context: Optional[bool] = None,
        only_need_prompt: Optional[bool] = None,
        response_type: Optional[str] = None,
        top_k: Optional[int] = None,
        chunk_top_k: Optional[int] = None,
        max_entity_tokens: Optional[int] = None,
        max_relation_tokens: Optional[int] = None,
        max_total_tokens: Optional[int] = None,
        conversation_history: Optional[List[dict]] = None,
        history_turns: Optional[int] = None,
        ids: Optional[List[str]] = None,
        user_prompt: Optional[str] = None,
        enable_rerank: Optional[bool] = None
    ) -> LrQueryResponse:
        """
        Query the LightRAG knowledge graph.

        Args:
            query: The query text
            mode: Query mode (local, global, hybrid, naive, mix, bypass). Defaults to "mix"
            only_need_context: If True, only returns the retrieved context without generating a response
            only_need_prompt: If True, only returns the generated prompt without producing a response
            response_type: Defines the response format (e.g., 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points')
            top_k: Number of top items to retrieve
            chunk_top_k: Number of text chunks to retrieve initially from vector search
            max_entity_tokens: Maximum tokens allocated for entity context
            max_relation_tokens: Maximum tokens allocated for relationship context
            max_total_tokens: Maximum total tokens budget for the entire query context
            conversation_history: Past conversation history to maintain context
            history_turns: Number of complete conversation turns to consider
            ids: List of ids to filter the results
            user_prompt: User-provided prompt for the query
            enable_rerank: Enable reranking for retrieved text chunks

        Returns:
            QueryResponse: The response from LightRAG

        Raises:
            httpx.HTTPError: If there's an HTTP error during the request
            Exception: For any other unexpected errors
        """
        try:
            # Create the request payload
            request_data = LrQueryRequest(
                query=query,
                mode=mode,
                only_need_context=only_need_context,
                only_need_prompt=only_need_prompt,
                response_type=response_type,
                top_k=top_k,
                chunk_top_k=chunk_top_k,
                max_entity_tokens=max_entity_tokens,
                max_relation_tokens=max_relation_tokens,
                max_total_tokens=max_total_tokens,
                conversation_history=conversation_history,
                history_turns=history_turns,
                ids=ids,
                user_prompt=user_prompt,
                enable_rerank=enable_rerank
            )

            # Send the query request to LightRAG
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/query",
                    json=request_data.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=60.0  # Queries might take longer than inserts
                )

                response.raise_for_status()

                # Parse the response
                response_data = response.json()
                query_response = LrQueryResponse(**response_data)

                self.logger.info(
                    f"Successfully executed query: '{query[:50]}...' with mode '{mode}'"
                )

                return query_response

        except httpx.HTTPError as e:
            self.logger.error(
                f"HTTP error during query '{query[:50]}...': {e}")
            raise

        except Exception as e:
            self.logger.error(
                f"Unexpected error during query '{query[:50]}...': {e}")
            raise

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _insert_document(self, rq: LrInsertRequest) -> LrInsertResponse:
        """
        Insert a document into the LightRAG knowledge graph.

        Args:
            text: The text content of the document
            file_source: The source of the document (e.g., file path, URL)

        Returns:
            InsertResponse: The response from LightRAG
        """
        try:
            # Send the insert request to LightRAG
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/insert",
                    json=rq.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=60.0
                )

                response.raise_for_status()

                # Parse the response
                response_data = response.json()
                insert_response = LrInsertResponse(**response_data)

                self.logger.info(
                    f"Successfully executed insert for document from '{rq.file_source}'"
                )

                return insert_response

        except httpx.HTTPError as e:
            return LrInsertResponse(
                status="failure",
                message=f"HTTP error: {str(e)}",
                track_id=""
            )

        except Exception as e:
            return LrInsertResponse(
                status="failure",
                message=f"Unexpected error: {str(e)}",
                track_id=""
            )
