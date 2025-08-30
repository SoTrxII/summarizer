from typing import List

from pydantic import BaseModel, Field

from .base_models import BaseCharacter, CharacterUpdate, ItemOrClue, NPCInfo, OpenThread


class CampaignCharacter(BaseCharacter):
    """A character in the campaign without speaker identification."""
    pass


class StoryArc(BaseModel):
    """Major story arc spanning multiple episodes."""
    title: str = Field(..., description="Name or title of the story arc")
    description: str = Field(..., description="Description of the story arc")
    episodes_involved: List[str] = Field(
        default_factory=list,
        description="Episode identifiers where this arc appears"
    )
    status: str = Field(
        default="ongoing",
        description="Status: 'ongoing', 'completed', 'paused'"
    )


class CampaignSummary(BaseModel):
    """Structured summary of an entire RPG campaign."""
    campaign_overview: str = Field(
        ...,
        description="Brief summary of the entire campaign, including tone, setting, and main story arc"
    )
    player_characters: List[CampaignCharacter] = Field(
        default_factory=list,
        description="All player characters that participated in the campaign with their final descriptions"
    )
    major_story_arcs: List[StoryArc] = Field(
        default_factory=list,
        description="Key story arcs spanning multiple episodes"
    )
    character_development: List[CharacterUpdate] = Field(
        default_factory=list,
        description="Character development highlights across the entire campaign"
    )
    notable_npcs: List[NPCInfo] = Field(
        default_factory=list,
        description="Important NPCs introduced or developed throughout the campaign"
    )
    important_items_and_clues: List[ItemOrClue] = Field(
        default_factory=list,
        description="Significant items, artifacts, or clues discovered in the campaign"
    )
    unresolved_threads: List[OpenThread] = Field(
        default_factory=list,
        description="Outstanding questions, hooks, or storylines left unresolved"
    )
    continuity_notes: str = Field(
        ...,
        description="Notes on continuity, recurring themes, or callbacks between episodes"
    )
