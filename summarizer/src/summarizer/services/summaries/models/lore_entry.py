from difflib import SequenceMatcher
from typing import List, Optional, Self

from pydantic import BaseModel, Field

from .traits import Clusterable


class LoreEntry(BaseModel, Clusterable):
    """
    Represents a lore entry in the game world.
    """
    lore_id: str = Field(..., description="Canonical lore id (slug)")
    title: Optional[str] = Field(None, description="Short title")
    description: str = Field(..., description="Concise lore text")
    from_episode: str = Field(...,
                              description="Episode number the lore was first introduced")

    def __str__(self) -> str:
        title_text = f" - {self.title}" if self.title else ""
        return f"{self.lore_id}{title_text}: {self.description} (from episode {self.from_episode})"

    def similarity_to(self, other: Self) -> float:
        """
        Calculate description similarity with another lore entry using SequenceMatcher.
        Returns a value between 0.0 and 1.0.
        """
        return SequenceMatcher(None, self.description.lower(),
                               other.description.lower()).ratio()

    def can_merge_with(self, other: Self, similarity_threshold: float = 0.9) -> bool:
        """
        Check if this lore entry can be merged with another.
        Entries can be merged if they have the same lore_id or very similar descriptions.
        """
        return (self.lore_id == other.lore_id or
                self.similarity_to(other) >= similarity_threshold)

    def merge_with(self, other: Self) -> Self:
        """
        Merge this lore entry with another, returning a new merged entry.
        Preserves the most complete information from both entries.
        """
        # Choose the most complete title
        merged_title = self.title
        if other.title and (not self.title or len(other.title) > len(self.title)):
            merged_title = other.title

        # Choose the most detailed description
        merged_description = (self.description if len(self.description) > len(other.description)
                              else other.description)

        # Use the first episode mentioned
        merged_from_episode = min(
            self.from_episode, other.from_episode, key=str)

        # Prefer the existing lore_id, or the more descriptive one
        merged_lore_id = self.lore_id if self.lore_id else other.lore_id

        return self.__class__(
            lore_id=merged_lore_id,
            title=merged_title,
            description=merged_description,
            from_episode=merged_from_episode
        )

    @classmethod
    def aggregate(cls, items: List[Self], similarity_threshold: float = 0.9) -> List[Self]:
        """
        Aggregate a list of lore entries, merging duplicates and similar entries.
        """
        if not items:
            return []

        aggregated = []

        for lore in items:
            merged = False

            # Try to merge with existing lore entries
            for i, existing in enumerate(aggregated):
                if lore.can_merge_with(existing, similarity_threshold):
                    aggregated[i] = existing.merge_with(lore)
                    merged = True
                    break

            if not merged:
                aggregated.append(lore)

        return aggregated
