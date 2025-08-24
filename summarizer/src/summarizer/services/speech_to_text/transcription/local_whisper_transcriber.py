import logging
from pathlib import Path
from typing import Any, Dict, Literal

from whisperx import load_audio, load_model


class LocalWhisperTranscriber:
    """
    Local Whisper transcription implementation using WhisperX.
    """

    def __init__(self, device: Literal["cpu", "cuda"] = "cpu", model_size: Literal["base", "medium"] = "medium") -> None:
        self.device = device
        self.compute_type = "int8"

        self.model = load_model(
            model_size, self.device, compute_type=self.compute_type
        )

    async def transcribe_audio(self, audio_file: Path) -> Dict[str, Any]:
        """
        Transcribe audio using local Whisper model.

        Args:
            audio_file: Path to the audio file

        Returns:
            Dictionary containing transcription result with segments
        """
        logging.info(
            f"Transcribing audio file with local Whisper: {audio_file}")
        audio = load_audio(audio_file)

        # Audio -> Text
        result = self.model.transcribe(audio, batch_size=16)
        return result
