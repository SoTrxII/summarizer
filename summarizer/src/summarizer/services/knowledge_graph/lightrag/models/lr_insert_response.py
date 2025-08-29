from pydantic import BaseModel


class LrInsertResponse(BaseModel):
    """Response model for insert operations."""
    # Ok / KO
    status: str
    # Success / Error message
    message: str
    # Operation uuid
    track_id: str
