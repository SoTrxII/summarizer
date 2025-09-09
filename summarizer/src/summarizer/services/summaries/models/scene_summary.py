from typing import List, Optional

from pydantic import BaseModel, Field

from .base_models import NPC, Event, LoreEntry, PlayerCharacter, Timestamps


class SceneSummary(BaseModel):
    # Metadata
    schema_version: str = Field("1.0", description="Schema version")
    timestamps: Timestamps = Field(..., description="Scene start/end")

    # "Human" attributes
    human_summary: str = Field(
        ..., description="Summary with all the infos necessary for a player having missed the session to catch up")

    # "Machine readable" attributes
    events: List[Event] = Field(default_factory=list)
    world_lore: List[LoreEntry] = Field(default_factory=list)
    player_characters: List[PlayerCharacter] = Field(default_factory=list)
    npcs: List[NPC] = Field(default_factory=list)

    def to_text(self) -> str:
        text_parts = []

        # Scene header
        text_parts.append("Scene Summary")
        text_parts.append(
            f"[Timestamp: {self.timestamps.start:.1f}s - {self.timestamps.end:.1f}s]")
        text_parts.append("")

        # Scene summary
        text_parts.append("Summary:")
        text_parts.append(self.human_summary)
        text_parts.append("")

        # World Lore
        if self.world_lore:
            text_parts.append("World Lore:")
            for lore in self.world_lore:
                text_parts.append(f"- {lore.description}")
            text_parts.append("")

        # Player characters
        if self.player_characters:
            text_parts.append("Player Characters:")
            for character in self.player_characters:
                text_parts.append(
                    f"- {character.name}: {character.description}")
            text_parts.append("")

        # NPCs
        if self.npcs:
            text_parts.append("NPCs:")
            for npc in self.npcs:
                text_parts.append(f"- {npc.name}: {npc.description}")
            text_parts.append("")

        return "\n".join(text_parts)
