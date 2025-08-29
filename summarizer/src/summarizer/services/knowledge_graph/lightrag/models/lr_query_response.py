
from pydantic import BaseModel, Field


class LrQueryResponse(BaseModel):
    """Response model for LightRAG queries."""

    response: str = Field(description="The generated response")
