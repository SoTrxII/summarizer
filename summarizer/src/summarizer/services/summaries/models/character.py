
from difflib import SequenceMatcher
from typing import List, Optional, Self

from pydantic import BaseModel, Field

from .traits import Clusterable


class Character(BaseModel, Clusterable):
    """
    Represents a character in the game world.
    """
    character_id: str = Field(..., description="Canonical character id (slug)")

    name: str = Field(..., description="Display name")

    aliases: List[str] = Field(default_factory=list, description="Other names")

    description: Optional[str] = Field(
        None, description="Character physical description")

    def __str__(self) -> str:
        aliases_text = f" (also known as: {', '.join(self.aliases)})" if self.aliases else ""
        description_text = f": {self.description}" if self.description else ""
        return f"{self.name}{aliases_text}{description_text}"

    def name_similarity_to(self, other: Self) -> float:
        """
        Calculate name similarity with another character using SequenceMatcher.
        Returns a value between 0.0 and 1.0.
        """
        return SequenceMatcher(None, self.name.lower(), other.name.lower()).ratio()

    def has_name_in_aliases(self, other: Self) -> bool:
        """
        Check if this character's name appears in another character's aliases or vice versa.
        """
        return (self.name.lower() in [alias.lower() for alias in other.aliases] or
                other.name.lower() in [alias.lower() for alias in self.aliases])

    def can_merge_with(self, other: Self, similarity_threshold: float = 0.8) -> bool:
        """
        Check if this character can be merged with another character.
        Characters can be merged if they have the same character_id, similar names, or names in aliases.
        """
        return (self.character_id == other.character_id or
                self.name_similarity_to(other) >= similarity_threshold or
                self.has_name_in_aliases(other))

    def merge_with(self, other: Self) -> Self:
        """
        Merge this character with another, returning a new merged character.
        Combines aliases and preserves the most complete information.
        """
        # Merge aliases
        merged_aliases = list(self.aliases)
        for alias in other.aliases:
            if alias not in merged_aliases and alias.lower() != self.name.lower():
                merged_aliases.append(alias)

        # Add the other character's name as an alias if different
        if (other.name.lower() != self.name.lower() and
                other.name not in merged_aliases):
            merged_aliases.append(other.name)

        # Use the more detailed description
        merged_description = self.description
        if (other.description and
                (not self.description or len(other.description) > len(self.description))):
            merged_description = other.description

        # Prefer the existing character_id and name
        return self.__class__(
            character_id=self.character_id,
            name=self.name,
            aliases=merged_aliases,
            description=merged_description
        )

    @classmethod
    def aggregate(cls, items: List[Self], similarity_threshold: float = 0.8) -> List[Self]:
        """
        Aggregate a list of characters, merging duplicates and similar characters.
        """
        if not items:
            return []

        aggregated = []

        for char in items:
            merged = False

            # Try to merge with existing characters
            for i, existing in enumerate(aggregated):
                if char.can_merge_with(existing, similarity_threshold):
                    aggregated[i] = existing.merge_with(char)
                    merged = True
                    break

            if not merged:
                aggregated.append(char)

        return aggregated
