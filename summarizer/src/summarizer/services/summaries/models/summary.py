from typing import List, Self

from pydantic import BaseModel, Field

from .character import Character
from .event import Event
from .lore_entry import LoreEntry
from .timestamps import Timestamps


class Summary(BaseModel):
    # Metadata
    schema_version: str = Field("1.0", description="Schema version")
    timestamps: Timestamps = Field(
        ..., description="Start/end timestamps for the summarized content")

    human_summary: str = Field(
        ..., description="Summary with all the infos necessary for a player having missed the session to catch up")

    events: List[Event] = Field(
        default_factory=list, description="Key events that happened in the scene")

    world_lore: List[LoreEntry] = Field(
        default_factory=list, description="Lore entries mentioned or relevant to the scene")

    player_characters: List[Character] = Field(
        default_factory=list, description="Player characters involved in the scene")

    npcs: List[Character] = Field(default_factory=list,
                                  description="NPCs involved in the scene")

    @classmethod
    def merge(cls, items: List[Self]) -> Self:
        """
        Aggregate multiple scenes by merging events, lore, characters, and NPCs 
        while deduplicating using fuzzy search.

        :param scenes: List of scene summaries to aggregate
        :return: Dictionary containing aggregated data with overall timestamps
        """
        if not items:
            return cls(
                human_summary="",
                schema_version="v1.0",
                timestamps=Timestamps(start=0, end=0),
                events=[],
                npcs=[],
                player_characters=[],
                world_lore=[]
            )

        # Calculate overall timestamps
        start_time = min(scene.timestamps.start for scene in items)
        end_time = max(scene.timestamps.end for scene in items)

        # Collect all items from all scenes
        all_events = [event for scene in items for event in scene.events]
        all_lore = [lore for scene in items for lore in scene.world_lore]
        all_pcs = [char for scene in items for char in scene.player_characters]
        all_npcs = [char for scene in items for char in scene.npcs]

        return cls(
            # TODO : Handle merging different schema version when there will be
            schema_version=items[0].schema_version,
            human_summary="\n---\n".join([s.human_summary for s in items]),
            timestamps=Timestamps(start=start_time, end=end_time),
            events=Event.aggregate(all_events),
            world_lore=LoreEntry.aggregate(all_lore),
            player_characters=Character.aggregate(all_pcs),
            npcs=Character.aggregate(all_npcs)
        )

    def __str__(self) -> str:
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
                text_parts.append(str(lore))
            text_parts.append("")

        # Player characters
        if self.player_characters:
            text_parts.append("Player Characters:")
            for character in self.player_characters:
                text_parts.append(str(character))
            text_parts.append("")

        # NPCs
        if self.npcs:
            text_parts.append("NPCs:")
            for npc in self.npcs:
                text_parts.append(str(npc))
            text_parts.append("")

        return "\n".join(text_parts)


# TODO: Remove EpisodeSummary and SceneSummary if they do not diverge from Summary

class EpisodeSummary(Summary):
    ...


class SceneSummary(Summary):
    ...
