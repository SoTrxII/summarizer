from json import dumps, loads
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence

SILENCE_BREAK_SECONDS = 10
MIN_SCENE_DURATION_SECONDS = 5 * 60
SIM_THRESHOLD = 0.65
_embedder = SentenceTransformer("all-MiniLM-L6-v2")


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def group_into_scenes(sentences: List[Sentence]) -> List[Scene]:
    """
    Split a TTRPG transcript into scenes.
    A scene is a contiguous block of dialogue with a common theme.
    """

    scenes = []
    current = [sentences[0]]

    def flush_scene():
        if current:
            scenes.append({
                "start": current[0]["start"],
                "end": current[-1]["end"],
                "lines": current.copy()
            })
            current.clear()

    for prev, curr in zip(sentences, sentences[1:]):
        # ensure current is not empty
        if not current:
            current.append(curr)
            continue

        gap = curr["start"] - prev["end"]
        scene_duration = curr["end"] - current[0]["start"]

        # --- Scene break conditions ---
        break_scene = False

        # Long silence
        if gap > SILENCE_BREAK_SECONDS and scene_duration >= MIN_SCENE_DURATION_SECONDS:
            break_scene = True

        # Semantic shift
        elif scene_duration >= MIN_SCENE_DURATION_SECONDS and len(current) > 4:
            texts = [l["text"] for l in current]
            embeddings = _embedder.encode(texts)
            sim = _cos(np.mean(embeddings[:-1], axis=0), embeddings[-1])
            if sim < SIM_THRESHOLD:
                break_scene = True

        # --- If break detected ---
        if break_scene:
            flush_scene()

        current.append(curr)

    flush_scene()

    return scenes
