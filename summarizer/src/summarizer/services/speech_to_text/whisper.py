import logging
from pathlib import Path
from typing import List, Literal

from whisperx import (
    align,
    assign_word_speakers,
    load_align_model,
    load_audio,
    load_model,
)
from whisperx.diarize import DiarizationPipeline

from summarizer.models.sentence import Sentence


class WhisperX:
    """
    A text to speech implementation using WhisperX
    https://github.com/m-bain/whisperX
    """

    def __init__(self, hugging_face_token: str, *, device: Literal["cpu", "cuda"] = "cpu", model_size: Literal["base", "medium"] = "medium") -> None:

        # Device to run the model on
        self.device = device
        self.compute_type = "int8" if self.device == "cpu" else "float16"
        # Hugging Face token to retrieve restricted models
        self.hugging_face_token = hugging_face_token

        self.model = load_model(
            model_size, self.device, compute_type=self.compute_type
        )

    def transcribe(self, audio_path: Path, diarize: bool) -> List[Sentence]:
        logging.info(f"Transcribing audio file: {audio_path}")
        audio = load_audio(audio_path)

        # Audio -> Text
        result = self.model.transcribe(audio, batch_size=16)
        if not diarize:
            return [Sentence(**seg) for seg in result["segments"]]

        # Precisely align text with audio, this will help with speaker recognition
        align_model, metadata = load_align_model(
            language_code=result["language"], device=self.device
        )
        asr_aligned = align(
            result["segments"], align_model, metadata, audio, self.device, return_char_alignments=False
        )

        # Recognize speakers
        diarize_model = DiarizationPipeline(
            use_auth_token=self.hugging_face_token,
            device=self.device
        )
        result = assign_word_speakers(diarize_model(audio), asr_aligned)

        return self.__normalize_sentences(result)

    def __normalize_sentences(self, result: dict) -> List[Sentence]:
        """
            Fix inconsistencies transcription:
            - Add speaker labels
            - Merge small sentences into a single line if they are spoken by the same speaker and are close in time
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
