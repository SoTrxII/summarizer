from pydantic import BaseModel


class LrInsertRequest(BaseModel):
    """Request model for inserting text into LightRAG."""
    text: str
    file_source: str = ""
