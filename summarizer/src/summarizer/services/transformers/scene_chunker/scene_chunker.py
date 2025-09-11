from typing import List, Protocol

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence


class SceneChunker(Protocol):
    """
    A scene chunker can takes a whole TTRPG episode summary and split it into distinct scenes
    """

    def group_into_scenes(self, sentences: List[Sentence]) -> List[Scene]: ...
    """
        Group a transcript into scenes
    """
