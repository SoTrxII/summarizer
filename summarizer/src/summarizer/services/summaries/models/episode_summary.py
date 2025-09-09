from typing import List, Optional

from pydantic import BaseModel, Field

from .base_models import NPC, Event, LoreEntry, PlayerCharacter, Timestamps


class EpisodeSummary(BaseModel):
    # Metadata
    timestamps: Optional[Timestamps] = Field(None)
    schema_version: str = Field("1.0", description="Schema version")

    # "Human" attributes
    human_summary: str = Field(
        ..., description="Summary with all the infos necessary for a player having missed the session to catch up")

    # "Machine readable" attributes
    events: List[Event] = Field(default_factory=list)
    world_lore: List[LoreEntry] = Field(default_factory=list)
    player_characters: List[PlayerCharacter] = Field(default_factory=list)
    npcs: List[NPC] = Field(default_factory=list)
