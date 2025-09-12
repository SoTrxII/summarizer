from pydantic import BaseModel, Field


class Timestamps(BaseModel):
    """
    Represents a time window with start and end times in seconds.
    """
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @property
    def duration(self) -> float:
        return self.end - self.start
