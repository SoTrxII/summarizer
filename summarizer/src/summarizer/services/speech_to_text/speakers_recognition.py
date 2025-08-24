import logging
from pathlib import Path
from typing import Any, Dict, List, Literal

from pycountry import languages
from whisperx import (
    align,
    assign_word_speakers,
    load_align_model,
    load_audio,
)
from whisperx.diarize import DiarizationPipeline

from summarizer.models.sentence import Sentence


class SpeakersRecognition:
    """
    Service for aligning transcription with audio and performing speaker diarization.
    """

    def __init__(self, hugging_face_token: str, device: Literal["cpu", "cuda"] = "cpu"):
        """
        Args:
            hugging_face_token: Hugging Face token for accessing restricted models
            device: Device to run the models on
        """
        self.hugging_face_token = hugging_face_token
        self.device = device

    async def identify_speakers(
        self,
        audio_file: Path,
        transcription_result: Dict[str, Any]
    ) -> List[Sentence]:
        """
        Identify speakers in the audio file based on the transcription result.

        Args:
            audio_file: Path to the audio file
            transcription_result: Transcription result from a transcriber

        Returns:
            List of Sentence objects with speaker information
        """

        logging.info(f"Aligning and diarizing audio file: {audio_file}")
        audio = load_audio(audio_file)

        # Precisely align text with audio, this will help with speaker recognition
        language = transcription_result.get("language", "en")
        language_code = self._language_to_code(language)
        align_model, metadata = load_align_model(
            language_code=language_code, device=self.device
        )
        asr_aligned = align(
            transcription_result["segments"],
            align_model,
            metadata,
            audio,
            self.device,
            return_char_alignments=False
        )

        # Recognize speakers
        diarize_model = DiarizationPipeline(
            use_auth_token=self.hugging_face_token,
            device=self.device
        )
        result = assign_word_speakers(diarize_model(audio), asr_aligned)

        return self.__normalize_sentences(result)

    def __normalize_sentences(self, result: Dict[str, Any]) -> List[Sentence]:
        """
        Normalize transcription result into Sentence objects with speaker merging.

        Args:
            result: Transcription result dictionary

        Returns:
            List of normalized Sentence objects
        """
        # Normalize the segments to always have a speaker label
        utterances: List[Sentence] = []
        for seg in result["segments"]:
            speaker = seg.get("speaker", "SPEAKER_Unknown")
            start = float(seg["start"])
            end = float(seg["end"])
            text = seg["text"].strip()
            if text:
                utterance: Sentence = {
                    "start": start,
                    "end": end,
                    "speaker": speaker,
                    "text": text
                }
                utterances.append(utterance)

        # Merge sentences into a pseudo-paragraph if they are spoken by the same speaker and are close in time
        THRESHOLD = 0.8
        merged: List[Sentence] = []
        for current in utterances:
            previous = merged[-1] if merged else None
            if previous and current["speaker"] == previous["speaker"] and (current["start"] - previous["end"]) < THRESHOLD:
                previous["end"] = current["end"]
                previous["text"] += f" {current['text']}".strip()
            else:
                merged.append(current)

        return merged

    def _language_to_code(self, language_name: str, default="en") -> str:
        """
        Return the ISO 639-1 code for a given language name.
        """
        try:
            lang = languages.lookup(language_name)
            return lang.alpha_2  # ISO 639-1 code
        except LookupError:
            logging.warning(
                f"Unknown language '{language_name}', defaulting to '{default}'")
            return default
