"""Models for LightRAG query operations."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LrQueryRequest(BaseModel):
    """Request model for querying LightRAG."""

    query: str = Field(min_length=1, description="The query text")
    mode: str = Field(default="mix", description="Query mode",
                      pattern="^(local|global|hybrid|naive|mix|bypass)$")
    only_need_context: Optional[bool] = Field(
        default=None,
        description="If True, only returns the retrieved context without generating a response."
    )
    only_need_prompt: Optional[bool] = Field(
        default=None,
        description="If True, only returns the generated prompt without producing a response."
    )
    response_type: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Defines the response format. Examples: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'."
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of top items to retrieve. Represents entities in 'local' mode and relationships in 'global' mode."
    )
    chunk_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of text chunks to retrieve initially from vector search and keep after reranking."
    )
    max_entity_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of tokens allocated for entity context in unified token control system."
    )
    max_relation_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of tokens allocated for relationship context in unified token control system."
    )
    max_total_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum total tokens budget for the entire query context (entities + relations + chunks + system prompt)."
    )
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Stores past conversation history to maintain context. Format: [{'role': 'user/assistant', 'content': 'message'}]."
    )
    history_turns: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of complete conversation turns (user-assistant pairs) to consider in the response context."
    )
    ids: Optional[List[str]] = Field(
        default=None,
        description="List of ids to filter the results."
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="User-provided prompt for the query. If provided, this will be used instead of the default value from prompt template."
    )
    enable_rerank: Optional[bool] = Field(
        default=None,
        description="Enable reranking for retrieved text chunks. If True but no rerank model is configured, a warning will be issued. Default is True."
    )
