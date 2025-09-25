from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class Transcriber(Protocol):
    """
    Protocol for audio transcription services.

    Classes implementing this protocol must provide an async transcribe_audio method
    that takes an audio file path and returns a dictionary with transcription results.
    """

    async def transcribe_audio(self, audio_file: Path) -> Dict[str, Any]:
        """
        Transcribe audio to text with timestamps.

        Args:
            audio_file: Path to the audio file

        Returns:
            Dictionary containing transcription result with segments
        """
        ...
