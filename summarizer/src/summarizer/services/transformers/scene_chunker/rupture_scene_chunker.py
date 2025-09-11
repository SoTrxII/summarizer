from typing import Final, List, Literal

import numpy as np
import ruptures as rpt
from sentence_transformers import SentenceTransformer

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence


class RuptureSceneChunker:
    # Number of sentences per initial chunk for semantic analysis
    SENTENCES_PER_CHUNK: Final = 20

    # Minimum duration of a scene in seconds
    MIN_SCENE_DURATION_SECONDS: Final = 3 * 60  # 3 minutes minimum

    # Target duration per scene for penalty calculation (in minutes)
    # Aim for ~18 minutes per theatrical act
    TARGET_SCENE_DURATION_MINUTES: Final = 18

    _embedder: Final = SentenceTransformer("all-MiniLM-L6-v2")
    _device: Literal["cpu", "cuda"] = "cpu"

    def __init__(self, device: Literal["cpu", "cuda"] = "cpu"):
        """
        Initialize the scene chunker.

        Uses ruptures library to detect narrative change points in semantic embeddings,
        creating theatrical-style scenes based on statistical changes in content.
        """
        self._device = device

    def group_into_scenes(self, sentences: List[Sentence]) -> List[Scene]:
        """
        Group sentences into theatrical scenes using ruptures change point detection.

        This simplified approach uses only the ruptures library to detect statistically
        significant changes in semantic embeddings, creating natural narrative breaks.
        """
        if not sentences:
            return []

        # Step 1: Create chunks for semantic analysis
        chunks = []
        for i in range(0, len(sentences), self.SENTENCES_PER_CHUNK):
            chunk_sentences = sentences[i:i + self.SENTENCES_PER_CHUNK]
            if chunk_sentences:
                chunks.append(chunk_sentences)

        if not chunks:
            return []

        # Step 2: Compute embeddings for each chunk
        print(
            f"DEBUG: Created {len(chunks)} chunks from {len(sentences)} sentences")

        chunk_embeddings = []
        for chunk in chunks:
            texts = [s["text"] for s in chunk]
            sentence_embeddings = self._embedder.encode(
                texts, device=self._device)
            chunk_embedding = np.mean(sentence_embeddings, axis=0)
            chunk_embeddings.append(chunk_embedding)

        # Step 3: Use ruptures to detect change points
        change_points = self._detect_ruptures_change_points(
            chunk_embeddings, sentences)

        # Step 4: Create scenes from change points
        break_points = [0] + change_points + [len(chunks)]
        # Remove duplicates and sort
        break_points = sorted(list(set(break_points)))

        print(f"DEBUG: Final break points: {break_points}")

        scenes = self._create_scenes_from_breaks(chunks, break_points)

        # Step 5: Ensure scenes meet minimum duration requirements
        scenes = self._merge_short_scenes(scenes)

        # Step 6: Sort scenes chronologically
        scenes.sort(key=lambda scene: scene["start"])

        print(f"DEBUG: Created {len(scenes)} final scenes")
        return scenes

    def _detect_ruptures_change_points(self, embeddings: List[np.ndarray], sentences: List[Sentence]) -> List[int]:
        """Use ruptures to detect optimal change points in the embedding sequence."""
        if len(embeddings) < 5:
            return []

        try:
            # Convert embeddings to matrix format
            embedding_matrix = np.array(embeddings)

            # Validate data
            if np.any(np.isnan(embedding_matrix)) or embedding_matrix.shape[0] < 5:
                print("Warning: Invalid embedding data")
                return []

            # Calculate penalty based on content duration and target scene length
            total_duration = sentences[-1]["end"] - sentences[0]["start"]
            total_minutes = total_duration / 60
            target_scenes = max(
                3, int(total_minutes / self.TARGET_SCENE_DURATION_MINUTES))

            # Much more aggressive penalty calculation
            # Lower penalty = more change points = more scenes
            base_penalty = max(0.1, len(embeddings) /
                               (target_scenes * 4))  # Much more sensitive
            # Cap at 3.0 to ensure we get change points
            penalty = min(3.0, base_penalty)

            print(
                f"DEBUG: Total duration: {total_minutes:.1f}min, target scenes: {target_scenes}, penalty: {penalty:.2f}")

            # Try multiple algorithms for better detection
            change_points = []

            # Method 1: Pelt with very low penalty
            algo = rpt.Pelt(model="l2", min_size=1, jump=1)
            algo.fit(embedding_matrix)
            pelt_points = algo.predict(pen=penalty)
            pelt_points = [cp for cp in pelt_points[:-1]
                           if 0 < cp < len(embeddings)]
            change_points.extend(pelt_points)

            # Method 2: Binary Segmentation for guaranteed results
            try:
                algo_bin = rpt.Binseg(model="l2", min_size=1)
                algo_bin.fit(embedding_matrix)
                n_bkps = min(target_scenes + 1, len(embeddings) // 3)
                bin_points = algo_bin.predict(n_bkps=n_bkps)
                bin_points = [cp for cp in bin_points[:-1]
                              if 0 < cp < len(embeddings)]
                change_points.extend(bin_points)
            except Exception as e:
                print(f"Binary segmentation failed: {e}")

            # Remove duplicates and sort
            change_points = sorted(list(set(change_points)))

            print(
                f"DEBUG: Combined methods found {len(change_points)} change points: {change_points}")

            return change_points

        except Exception as e:
            print(f"Warning: Ruptures detection failed: {e}")
            # Fallback: create scenes based on time only
            return self._fallback_time_based_breaks(sentences)

    def _fallback_time_based_breaks(self, sentences: List[Sentence]) -> List[int]:
        """Fallback method using time-based breaks when ruptures fails."""
        if not sentences:
            return []

        target_duration = self.TARGET_SCENE_DURATION_MINUTES * 60  # Convert to seconds

        # Calculate where to break based on time
        breaks = []
        current_time = sentences[0]["start"]

        chunk_size = self.SENTENCES_PER_CHUNK
        for i in range(chunk_size, len(sentences), chunk_size):
            if sentences[i]["start"] - current_time > target_duration:
                breaks.append(i // chunk_size)
                current_time = sentences[i]["start"]

        print(
            f"DEBUG: Fallback created {len(breaks)} time-based breaks: {breaks}")
        return breaks

    def _create_scenes_from_breaks(self, chunks: List[List[Sentence]], break_points: List[int]) -> List[Scene]:
        """Create scenes from validated break points."""
        scenes = []

        for i in range(len(break_points) - 1):
            start_chunk_idx = break_points[i]
            end_chunk_idx = break_points[i + 1]

            scene_chunks = chunks[start_chunk_idx:end_chunk_idx]
            if scene_chunks:
                all_sentences = []
                for chunk in scene_chunks:
                    all_sentences.extend(chunk)

                all_sentences.sort(key=lambda s: s["start"])

                scene = {
                    "start": all_sentences[0]["start"],
                    "end": all_sentences[-1]["end"],
                    "lines": all_sentences
                }
                scenes.append(scene)

        return scenes

    def _merge_short_scenes(self, scenes: List[Scene]) -> List[Scene]:
        """Merge scenes that are shorter than minimum duration with adjacent scenes."""
        if not scenes:
            return scenes

        merged_scenes = []
        i = 0

        while i < len(scenes):
            current_scene = scenes[i]
            scene_duration = current_scene["end"] - current_scene["start"]

            # If scene is too short, try to merge with the next scene
            if (scene_duration < self.MIN_SCENE_DURATION_SECONDS and
                i < len(scenes) - 1 and
                    len(merged_scenes) == 0):  # Only merge if it's the first scene

                next_scene = scenes[i + 1]

                # Merge current scene with next scene
                merged_lines = current_scene["lines"] + next_scene["lines"]
                merged_lines.sort(key=lambda s: s["start"])

                merged_scene = {
                    "start": merged_lines[0]["start"],
                    "end": merged_lines[-1]["end"],
                    "lines": merged_lines
                }

                merged_scenes.append(merged_scene)
                i += 2  # Skip the next scene since we merged it

            elif (scene_duration < self.MIN_SCENE_DURATION_SECONDS and
                  len(merged_scenes) > 0):  # Merge with previous scene

                prev_scene = merged_scenes[-1]
                merged_lines = prev_scene["lines"] + current_scene["lines"]
                merged_lines.sort(key=lambda s: s["start"])

                merged_scenes[-1] = {
                    "start": merged_lines[0]["start"],
                    "end": merged_lines[-1]["end"],
                    "lines": merged_lines
                }
                i += 1

            else:
                # Scene is long enough, keep as is
                merged_scenes.append(current_scene)
                i += 1

        return merged_scenes
