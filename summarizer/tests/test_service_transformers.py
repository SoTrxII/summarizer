from json import dump
from pathlib import Path

import pytest

from summarizer.models.sentence import Sentence
from summarizer.services.transformers import SceneChunker

from .utils.json import read_test_data


@pytest.mark.asyncio
async def test_service_speech_to_text_whisper(data_dir: Path):
    sentences = read_test_data(
        data_dir / "transcriptions" / "1m_sample2_diarized.json", Sentence)
    chunker = SceneChunker("cpu")
    scenes = chunker.group_into_scenes(sentences)

    # Ensure the directory exists before writing the file
    output_dir = data_dir / "generated" / "scenes"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "1m_sample2_scenes.json", "w") as f:
        dump(scenes, f)

    assert scenes is not None
    assert len(scenes) > 0
