from typing import List

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence


class NaiveTimeBasedChunker:
    """Simple time-based scene chunker for comparison."""

    def __init__(self, target_scene_minutes: float = 18):
        self.target_scene_minutes = target_scene_minutes
        self.min_scene_minutes = 3

    def group_into_scenes(self, sentences: List[Sentence]) -> List[Scene]:
        """Create scenes based purely on time intervals."""
        if not sentences:
            return []

        scenes = []
        current_scene_sentences = []
        scene_start_time = sentences[0]["start"]
        target_duration = self.target_scene_minutes * 60  # Convert to seconds

        for sentence in sentences:
            current_scene_sentences.append(sentence)
            elapsed_time = sentence["end"] - scene_start_time

            # Create new scene if we've exceeded target duration
            if elapsed_time >= target_duration and len(current_scene_sentences) > 10:
                # Finish current scene
                scene = {
                    "start": current_scene_sentences[0]["start"],
                    "end": current_scene_sentences[-1]["end"],
                    "lines": current_scene_sentences.copy()
                }
                scenes.append(scene)

                # Start new scene
                current_scene_sentences = []
                scene_start_time = sentence["start"]

        # Add final scene if it has content
        if current_scene_sentences:
            scene = {
                "start": current_scene_sentences[0]["start"],
                "end": current_scene_sentences[-1]["end"],
                "lines": current_scene_sentences
            }
            scenes.append(scene)

        return scenes
