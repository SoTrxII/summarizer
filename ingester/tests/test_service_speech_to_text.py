import json
import logging
import time
import warnings
from os import environ
from pathlib import Path

import pytest
import torch

from summarizer.services.speech_to_text import (
    SpeechToTextService,
)
from summarizer.services.speech_to_text.transcription import (
    AzureOpenAITranscriber,
    LocalWhisperTranscriber,
)

# Suppress specific warnings
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")


@pytest.mark.asyncio
async def test_service_speech_to_text_transcriber_azure(data_dir: Path, azure_transcribe: AzureOpenAITranscriber):
    sample_audio = data_dir / "audios" / "1m_sample1.ogg"
    # sample_audio = data_dir / "past_campaigns" / "bigger-than-25MB.ogg"

    # Start timing
    start_time = time.time()

    sentences = await azure_transcribe.transcribe_audio(sample_audio)

    # End timing and log the duration
    end_time = time.time()
    duration = end_time - start_time

    # Ensure the directory exists before writing the file
    output_dir = data_dir / "generated" / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "1m_sample1.json", "w") as f:
        json.dump(sentences, f)

    assert sentences is not None
    assert len(sentences) > 0

    logging.info(f"Transcription completed in {duration:.2f} seconds")
    logging.info(f"Transcription result: {sentences}")


@pytest.mark.asyncio
async def test_service_speech_to_text_transcriber_azure_concurrent(data_dir: Path, azure_transcribe: AzureOpenAITranscriber):
    sample_audio = data_dir / "audios" / "1m_sample1.ogg"
    azure_transcribe.set_concurrency(2)
    # sample_audio = data_dir / "past_campaigns" / "bigger-than-25MB.ogg"

    # Start timing
    start_time = time.time()

    result = await azure_transcribe.transcribe_audio(sample_audio)

    # End timing and log the duration
    end_time = time.time()
    duration = end_time - start_time

    # Ensure the directory exists before writing the file
    output_dir = data_dir / "generated" / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    # with open(output_dir / "1m_sample1.json", "w") as f:
    #     json.dump(sentences, f)

    # Verify the result structure
    assert result is not None
    assert isinstance(result, dict)
    assert "segments" in result
    assert "language" in result
    assert isinstance(result["segments"], list)
    assert len(result["segments"]) > 0

    # Verify segment structure
    for segment in result["segments"]:
        assert "start" in segment
        assert "end" in segment
        assert "text" in segment
        assert isinstance(segment["start"], (int, float))
        assert isinstance(segment["end"], (int, float))
        assert isinstance(segment["text"], str)
        assert segment["start"] <= segment["end"]

    logging.info(f"Transcription completed in {duration:.2f} seconds")
    logging.info(f"Transcription result: {result["segments"]}")


@pytest.mark.asyncio
async def test_service_speech_to_text_transcriber_local(data_dir: Path):
    hf_token = environ["HUGGING_FACE_TOKEN"]
    if not hf_token:
        raise ValueError("HUGGING_FACE_TOKEN environment variable is not set")

    # Auto-detect device: use cuda if available and compatible, otherwise cpu
    device = "cuda" if torch.cuda.is_available(
    ) and torch.cuda.get_device_capability()[0] >= 7 else "cpu"
    logging.info(f"Using device: {device}")

    whisper = LocalWhisperTranscriber(device)
    # sample_audio = data_dir / "past_campaigns" / "bigger-than-25MB.ogg"

    sample_audio = data_dir / "audios" / "1m_sample1.ogg"

    # Start timing
    start_time = time.time()

    sentences = await whisper.transcribe_audio(sample_audio)

    # End timing and log the duration
    end_time = time.time()
    duration = end_time - start_time

    assert sentences is not None
    assert len(sentences) > 0

    logging.info(f"Transcription completed in {duration:.2f} seconds")
    logging.info(f"Transcription result: {sentences}")


@pytest.mark.asyncio
async def test_service_speech_to_text(data_dir: Path, speech_to_text: SpeechToTextService):
    sample_audio = data_dir / "audios" / "1m_sample2.ogg"

    # Start timing
    start_time = time.time()

    sentences = await speech_to_text.transcribe(sample_audio, diarize=True)

    # End timing and log the duration
    end_time = time.time()
    duration = end_time - start_time

    # Ensure the directory exists before writing the file
    output_dir = data_dir / "generated" / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "1m_sample2_diarized.json", "w") as f:
        json.dump(sentences, f)

    assert sentences is not None
    assert len(sentences) > 0

    logging.info(f"Transcription completed in {duration:.2f} seconds")
    logging.info(f"Transcription result: {sentences}")
