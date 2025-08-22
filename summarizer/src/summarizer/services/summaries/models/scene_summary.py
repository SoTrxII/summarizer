from typing import List

from pydantic import BaseModel, Field

from .base_models import ItemOrClue, OpenThread, Timestamps


class PlayerAction(BaseModel):
    """Actions and statements by players during a scene."""
    speaker: str = Field(..., description="Player name or character name")
    content: str = Field(..., description="Action or statement by player")
    mode: str = Field(
        default="in_character",
        description="'in_character' or 'meta' for table jokes / side notes"
    )


class SceneSummary(BaseModel):
    """Summary of a single scene within an RPG session."""
    gm_content: str = Field(
        ...,
        description="GM narration, world info, NPCs, locations, lore"
    )
    player_actions: List[PlayerAction] = Field(
        default_factory=list,
        description="List of player actions and statements"
    )
    items_and_clues: List[ItemOrClue] = Field(
        default_factory=list,
        description="Items, clues, or objects of note discovered in this scene"
    )
    open_threads: List[OpenThread] = Field(
        default_factory=list,
        description="Unresolved hooks or questions arising from this scene"
    )
    timestamps: Timestamps = Field(
        ...,
        description="Start and end timestamps of the scene"
    )
