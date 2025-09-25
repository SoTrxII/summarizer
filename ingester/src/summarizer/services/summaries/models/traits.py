from abc import ABC, abstractmethod
from typing import List


class Clusterable[T](ABC):
    """
    Trait marking that object T can be merged with semantically identical objects
    """
    @abstractmethod
    def can_merge_with(self, other: T,  similarity_threshold: float) -> bool:
        """
        Check if this object can be merged with another object.
        """
        ...

    @abstractmethod
    def merge_with(self, other: T) -> T:
        """
        Merge this object with another object.
        """
        ...

    @classmethod
    @abstractmethod
    def aggregate(cls, items: List[T], similarity_threshold: float) -> List[T]:
        """
        Merge similar entries in a list of T
        """
        ...
