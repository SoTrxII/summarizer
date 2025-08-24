import logging
from pathlib import Path
from typing import Any, Dict

from openai import AzureOpenAI


class AzureOpenAITranscriber:
    """
    Azure OpenAI GPT-4o transcription implementation.
    """

    def __init__(self, endpoint: str, api_key: str, deployment_name: str):
        """
        Args:
            endpoint: Azure OpenAI resource endpoint
            api_key: Azure OpenAI API key
            deployment_name: GPT-4o transcribe deployment name
        """
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-03-01-preview"
        )
        self._deployment_name = deployment_name

    async def transcribe_audio(self, audio_file: Path) -> Dict[str, Any]:
        """
        Transcribe audio using Azure OpenAI GPT-4o.

        Args:
            audio_file: Path to the audio file

        Returns:
            Dictionary containing transcription result with segments
        """
        logging.info(
            f"Transcribing audio file with Azure OpenAI GPT-4o: {audio_file}")

        with open(audio_file, "rb") as f:
            response = self._client.audio.transcriptions.create(
                model=self._deployment_name,
                file=f,
                response_format="verbose_json"
            )

        if not response.segments:
            logging.warning("No segments found in transcription response.")
            return {"segments": []}

        # Convert Azure OpenAI response to the same format as WhisperX
        segments = []
        for seg in response.segments:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })

        return {
            "segments": segments,
            "language": getattr(response, 'language', 'en')
        }
