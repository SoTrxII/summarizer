"""
Base models for RPG session summaries to ensure consistency across scene, episode, and campaign levels.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class BaseCharacter(BaseModel):
    """Base character model with common fields."""
    name: str = Field(..., description="Character name")
    description: str = Field(
        ...,
        description="Physical appearance, personality, or other identifying traits"
    )


class CharacterUpdate(BaseModel):
    """Character information and development updates."""
    name: str = Field(..., description="Character or player name")
    changes: List[str] = Field(
        default_factory=list,
        description="Changes, decisions, or developments for this character"
    )


class NPCInfo(BaseModel):
    """Non-player character information."""
    name: str = Field(..., description="NPC name")
    details: List[str] = Field(
        default_factory=list,
        description="Details introduced or updated about this NPC"
    )


class ItemOrClue(BaseModel):
    """Items, clues, or notable objects."""
    name: str = Field(...,
                      description="Name or brief description of the item/clue")
    description: Optional[str] = Field(
        None,
        description="Additional details about the item or clue"
    )
    significance: Optional[str] = Field(
        None,
        description="Why this item/clue is important"
    )


class OpenThread(BaseModel):
    """Unresolved storylines, questions, or hooks."""
    description: str = Field(...,
                             description="Description of the unresolved thread")
    priority: Optional[str] = Field(
        None,
        description="Priority level: 'high', 'medium', 'low'"
    )
    related_characters: List[str] = Field(
        default_factory=list,
        description="Characters involved in this thread"
    )


class Timestamps(BaseModel):
    """Time markers for audio/video content."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @property
    def duration(self) -> float:
        """Calculate duration in seconds."""
        return self.end - self.start
