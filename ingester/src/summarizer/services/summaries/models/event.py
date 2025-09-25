from difflib import SequenceMatcher
from typing import List, Optional, Self

from pydantic import BaseModel, Field

from .timestamps import Timestamps
from .traits import Clusterable


class Event(BaseModel, Clusterable):
    """
    Represents a significant event that happened during the game.
    """
    timestamps: Timestamps = Field(..., description="Event time window")
    description: str = Field(..., description="What happened")
    actors: List[str] = Field(default_factory=list,
                              description="List of character_ids involved")
    scene_impact: Optional[str] = Field(
        None, description="Short note why it matters")

    def __str__(self) -> str:
        actors_text = f" [Involved: {', '.join(self.actors)}]" if self.actors else ""
        return f"- [{self.timestamps.start:.1f}s - {self.timestamps.end:.1f}s]{actors_text}: {self.description}"

    def overlaps_with(self, other: Self) -> bool:
        """
        Check if this event has overlapping time periods with another event.
        """
        return not (self.timestamps.end <= other.timestamps.start or
                    other.timestamps.end <= self.timestamps.start)

    def similarity_to(self, other: Self) -> float:
        """
        Calculate description similarity with another event using SequenceMatcher.
        Returns a value between 0.0 and 1.0.
        """
        return SequenceMatcher(None, self.description.lower(),
                               other.description.lower()).ratio()

    def can_merge_with(self, other: Self, similarity_threshold: float = 0.85) -> bool:
        """
        Check if this event can be merged with another event.
        Events can be merged if they overlap in time and have similar descriptions.
        """
        return (self.overlaps_with(other) and
                self.similarity_to(other) >= similarity_threshold)

    def merge_with(self, other: Self) -> Self:
        """
        Merge this event with another event, returning a new merged event.
        The merged event combines information from both events.
        """
        # Extend time window
        new_start = min(self.timestamps.start, other.timestamps.start)
        new_end = max(self.timestamps.end, other.timestamps.end)
        new_timestamps = Timestamps(start=new_start, end=new_end)

        # Merge actors
        merged_actors = list(self.actors)
        for actor in other.actors:
            if actor not in merged_actors:
                merged_actors.append(actor)

        # Combine scene impact
        merged_impact = None
        if self.scene_impact and other.scene_impact:
            if other.scene_impact not in self.scene_impact:
                merged_impact = f"{self.scene_impact} | {other.scene_impact}"
            else:
                merged_impact = self.scene_impact
        elif self.scene_impact or other.scene_impact:
            merged_impact = self.scene_impact or other.scene_impact

        # Choose the more detailed description
        merged_description = (self.description if len(self.description) > len(other.description)
                              else other.description)

        return self.__class__(
            timestamps=new_timestamps,
            description=merged_description,
            actors=merged_actors,
            scene_impact=merged_impact
        )

    @classmethod
    def aggregate(cls, items: List[Self], similarity_threshold: float = 0.85) -> List[Self]:
        """
        Aggregate a list of events, merging similar events with time overlap.
        """
        if not items:
            return []

        # Sort events by start time
        sorted_events = sorted(items, key=lambda e: e.timestamps.start)
        aggregated = []

        for event in sorted_events:
            merged = False

            # Try to merge with existing events
            for i, existing in enumerate(aggregated):
                if event.can_merge_with(existing, similarity_threshold):
                    aggregated[i] = existing.merge_with(event)
                    merged = True
                    break

            if not merged:
                aggregated.append(event)

        return aggregated
