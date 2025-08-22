from typing import List, TypedDict

from .sentence import Sentence


class Scene(TypedDict):
    """
    A TTRPG Scene
    """
    # The start time of the scene in seconds
    start: float
    # The end time of the scene in seconds
    end: float
    # The lines that make up the scene
    lines: List[Sentence]
