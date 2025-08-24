from pathlib import Path

import pytest

from summarizer.models.sentence import Sentence
from summarizer.services.transformers import SceneChunker

from .utils.json import read_test_data


@pytest.mark.asyncio
async def test_service_speech_to_text_whisper(data_dir: Path):
    sentences = read_test_data(
        data_dir / "transcriptions" / "10m_diarized.json", Sentence)
    chunker = SceneChunker("cpu")
    scenes = chunker.group_into_scenes(sentences)

    assert scenes is not None
    assert len(scenes) > 0
