import logging
from os import environ
from pathlib import Path

import pytest

from summarizer.services.speech_to_text.whisper import WhisperX


@pytest.mark.asyncio
async def test_service_speech_to_text_whisper(data_dir: Path):
    hf_token = environ["HUGGING_FACE_TOKEN"]
    if not hf_token:
        raise ValueError("HUGGING_FACE_TOKEN environment variable is not set")

    whisper = WhisperX(hf_token, device="cpu")
    sample_audio = data_dir / "audios" / "1m.ogg"

    sentences = whisper.transcribe(sample_audio, diarize=True)
    assert sentences is not None
    assert len(sentences) > 0
    logging.info(f"Transcription result: {sentences}")
