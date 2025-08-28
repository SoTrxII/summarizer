from typing import Final, List, Literal

import numpy as np
from sentence_transformers import SentenceTransformer

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence


class SceneChunker:
    """
    Chunk a TTRPG transcript into scenes. Scenes are a set of contiguous sentences
    that share a common theme or context.
    """

    # How many seconds of silence constitute a scene break
    SILENCE_BREAK_SECONDS: Final = 10

    # Minimum duration of a scene in seconds
    MIN_SCENE_DURATION_SECONDS: Final = 5 * 60

    # Similarity threshold for semantic shifts
    SIM_THRESHOLD: Final = 0.65

    # Sentence embedder for semantic similarity
    _embedder: Final = SentenceTransformer("all-MiniLM-L6-v2")

    # Device to run the embedding model on
    _device: Literal["cpu", "cuda"] = "cpu"

    def __init__(self, device: Literal["cpu", "cuda"] = "cpu"):
        self._device = device

    def _cos(self, a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _has_long_silence_break(self, gap: float) -> bool:
        """
        Check if there's a long silence break that warrants a scene break.

        Args:
            gap: Time gap between current and previous sentence

        Returns:
            True if there's a significant silence break
        """
        return gap > SceneChunker.SILENCE_BREAK_SECONDS

    def _has_semantic_shift(self, current_sentences: List[Sentence]) -> bool:
        """
        Check if there's a semantic shift that warrants a scene break.

        Args:
            current_sentences: List of sentences in the current scene

        Returns:
            True if there's a significant semantic shift
        """
        texts = [sentence["text"] for sentence in current_sentences]
        embeddings = self._embedder.encode(texts, device=self._device)

        # Calculate similarity between the average of all previous sentences and the last sentence
        similarity = self._cos(
            np.mean(embeddings[:-1], axis=0),
            embeddings[-1]
        )

        return similarity < SceneChunker.SIM_THRESHOLD

    def group_into_scenes(self, sentences: List[Sentence]) -> List[Scene]:
        """
        Split a TTRPG transcript into scenes.
        A scene is a contiguous block of dialogue with a common theme.
        """
        # List of identified scenes
        scenes: List[Scene] = []

        # Current sentences into the scene being built
        current: List[Sentence] = [sentences[0]]

        def flush_scene():
            if current:
                scenes.append({
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "lines": current.copy(),
                })
                current.clear()

        for prev, curr in zip(sentences, sentences[1:]):
            # A scene contains at least one sentence
            if not current:
                current.append(curr)
                continue

            gap = curr["start"] - prev["end"]
            scene_duration = curr["end"] - current[0]["start"]

            # A scene must be at least 5 minutes long and have more than 4 sentences
            # This is an arbitrary choice, but it helps to ensure that scenes are meaningful
            if scene_duration < SceneChunker.MIN_SCENE_DURATION_SECONDS or len(current) <= 4:
                current.append(curr)
                continue

            if self._has_long_silence_break(gap) or self._has_semantic_shift(current):
                flush_scene()

            current.append(curr)

        flush_scene()

        return scenes
