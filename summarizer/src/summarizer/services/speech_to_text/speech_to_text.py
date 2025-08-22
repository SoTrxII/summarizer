from pathlib import Path
from typing import List, Protocol

from summarizer.models.sentence import Sentence


class SpeechToText(Protocol):
    """
    Any speech to text class
    """

    def transcribe(self, audio_file: Path, diarize: bool = False) -> List[Sentence]:
        """
        Takes an audio file and transcribes it to text.
        param audio_path: Path to the audio file
        param diarize: Whether to perform speaker recognition

        return: The transcribed sentences
        """
        ...
