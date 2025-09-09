from typing import List, Optional

from pydantic import BaseModel, Field


class Timestamps(BaseModel):
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    model_config = {"extra": "forbid"}

    @property
    def duration(self) -> float:
        return self.end - self.start


class LoreEntry(BaseModel):
    lore_id: str = Field(..., description="Canonical lore id (slug)")
    title: Optional[str] = Field(None, description="Short title")
    description: str = Field(..., description="Concise lore text")
    provenance_scenes: List[str] = Field(default_factory=list)
    provenance_episodes: List[str] = Field(default_factory=list)
    first_seen_scene: Optional[str] = Field(None)
    first_seen_episode: Optional[str] = Field(None)


class CharacterBase(BaseModel):
    character_id: str = Field(..., description="Canonical id")
    name: str = Field(..., description="Display name")
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(None)
    first_seen: Optional[str] = Field(None)
    last_seen: Optional[str] = Field(None)


class NPC(CharacterBase):
    pass


class PlayerCharacter(CharacterBase):
    player_name: Optional[str] = Field(
        None, description="Human player's display name")
    in_scene: bool = Field(True, description="Present in this scene")
    model_config = {"extra": "forbid"}


class Event(BaseModel):
    event_id: str = Field(..., description="Unique event id")
    timestamps: Timestamps = Field(..., description="Event time window")
    description: str = Field(..., description="What happened")
    actors: List[str] = Field(default_factory=list,
                              description="List of character_ids involved")
    scene_impact: Optional[str] = Field(
        None, description="Short note why it matters")
