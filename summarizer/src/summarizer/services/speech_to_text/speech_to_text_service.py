import logging
from pathlib import Path
from typing import List

from summarizer.models.sentence import Sentence

from .speakers_recognition import SpeakersRecognition
from .transcription import Transcriber


class SpeechToTextService:

    def __init__(
        self,
        transcriber: Transcriber,
        diarizer: SpeakersRecognition
    ):
        """
        Args:
            transcriber: Audio -> Text
            diarizer: Recognize speakers in the audio and assign them to their sentences
        """
        self.transcriber = transcriber
        self.diarizer = diarizer

    async def transcribe(self, audio_file: Path, diarize: bool) -> List[Sentence]:
        """
        Transcribe an audio file to sentences with optional speaker diarization.

        Args:
            audio_file: Path to the audio file
            diarize: Whether to perform speaker diarization

        Returns:
            List of transcribed sentences
        """
        logging.info(f"Transcribing audio file: {audio_file}")

        # Step 1: Get transcription from the transcriber
        transcription_result = await self.transcriber.transcribe_audio(audio_file)

        if not transcription_result.get("segments"):
            logging.warning("No segments found in transcription result.")
            return []

        # Step 2: If no diarization requested, return simple sentences
        if not diarize:
            sentences = []
            for seg in transcription_result["segments"]:
                sentence = Sentence(
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    speaker="UNKNOWN",
                    text=seg["text"].strip()
                )
                sentences.append(sentence)
            return sentences

        # Step 3: Perform alignment and diarization
        return await self.diarizer.identify_speakers(audio_file, transcription_result)
