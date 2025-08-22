from typing import List

from pydantic import BaseModel, Field

from .base_models import CharacterUpdate, ItemOrClue, NPCInfo, OpenThread


class EpisodeSummary(BaseModel):
    """Summary of a complete RPG episode/session."""
    session_overview: str = Field(
        ...,
        description="High-level overview of the entire session"
    )
    key_events: List[str] = Field(
        default_factory=list,
        description="Ordered list of key events during the session"
    )
    character_updates: List[CharacterUpdate] = Field(
        default_factory=list,
        description="Character developments and changes during this episode"
    )
    npc_updates: List[NPCInfo] = Field(
        default_factory=list,
        description="NPCs introduced or updated in this episode"
    )
    items_and_clues: List[ItemOrClue] = Field(
        default_factory=list,
        description="Items, clues, or notable objects discovered"
    )
    open_threads: List[OpenThread] = Field(
        default_factory=list,
        description="Ongoing unresolved threads or questions"
    )
    continuity_notes: List[str] = Field(
        default_factory=list,
        description="Notes for maintaining story continuity between sessions"
    )
