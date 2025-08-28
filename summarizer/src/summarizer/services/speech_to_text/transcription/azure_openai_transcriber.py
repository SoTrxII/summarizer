import asyncio
import logging
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import whisperx
from openai import AzureOpenAI


class AzureOpenAITranscriber:
    """
    Azure OpenAI transcriber with automatic chunking and concurrent processing.

    Handles files larger than 25MB by splitting them into chunks and processes
    them concurrently while respecting API rate limits.
    """

    # These are the limit of the Azure service
    DEFAULT_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    DEFAULT_MAX_CONCURRENT_CALLS = 3
    API_VERSION = "2025-03-01-preview"

    DEFAULT_CONCURRENCY = 1  # 1 = no chunking, >1 = force chunking
    SAMPLE_RATE = 16000  # WhisperX default
    BYTES_PER_SAMPLE = 2  # 16-bit audio
    SAFETY_MARGIN = 0.9  # Use 90% of file size limit for safety

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        max_file_size: Optional[int] = DEFAULT_MAX_FILE_SIZE,
        concurrency: Optional[int] = DEFAULT_CONCURRENCY,
        max_concurrent_calls: Optional[int] = DEFAULT_MAX_CONCURRENT_CALLS,
    ) -> None:
        """
        Initialize the chunked transcriber.

        Args:
            endpoint: Azure OpenAI resource endpoint
            api_key: Azure OpenAI API key
            deployment_name: GPT-4o transcribe deployment name
            max_file_size: Maximum file size in bytes before chunking
            concurrency: Desired number of chunks (1=no chunking, >1=force chunking)
            max_concurrent_calls: Maximum concurrent API calls
        """
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=self.API_VERSION,
        )
        self._deployment_name = deployment_name
        self._max_file_size = max_file_size
        self._concurrency = concurrency
        self._max_concurrent_calls = max_concurrent_calls
        self._rate_limit_delay = 1.0 / max_concurrent_calls
        self._semaphore = asyncio.Semaphore(max_concurrent_calls)

    async def transcribe_audio(self, audio_file: Path) -> Dict[str, Any]:
        """
        Transcribe audio file with automatic chunking for large files.

        Args:
            audio_file: Path to the audio file

        Returns:
            Dictionary with 'segments' and 'language' keys
        """
        logging.info(f"Transcribing audio file: {audio_file}")

        file_size = os.path.getsize(audio_file)
        logging.info(f"Audio file size: {file_size / (1024*1024):.2f} MB")

        if self._should_use_chunking(file_size):
            return await self._transcribe_chunked_file(audio_file)
        else:
            return await self._transcribe_single_file(audio_file)

    def set_concurrency(self, new: int):
        self._concurrency = new

    def _should_use_chunking(self, file_size: int) -> bool:
        """Determine if file should be processed with chunking."""
        # Force chunking if concurrency > 1
        if self._concurrency > 1:
            logging.info(
                f"Using chunking for concurrent processing (concurrency={self._concurrency})")
            return True

        # Use chunking if file exceeds size limit
        if file_size > self._max_file_size:
            logging.info("Using chunking due to file size limit")
            return True

        return False

    async def _transcribe_single_file(self, audio_file: Path) -> Dict[str, Any]:
        """Transcribe a single audio file."""
        async with self._semaphore:
            await asyncio.sleep(self._rate_limit_delay)

            with open(audio_file, "rb") as f:
                response = self._client.audio.transcriptions.create(
                    model=self._deployment_name,
                    file=f,
                    response_format="verbose_json"
                )
            return self._format_transcription_response(response)

    def _format_transcription_response(self, response) -> Dict[str, Any]:
        """Format the API response into standard format."""
        if not response.segments:
            logging.warning("No segments found in transcription response.")
            return {"segments": []}

        segments = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            }
            for seg in response.segments
        ]

        return {
            "segments": segments,
            "language": getattr(response, 'language', 'en')
        }

    async def _transcribe_chunked_file(self, audio_file: Path) -> Dict[str, Any]:
        """Split audio file into chunks and transcribe them concurrently."""
        logging.info("Processing audio file with chunking enabled")

        audio = whisperx.load_audio(str(audio_file))
        total_duration = len(audio) / self.SAMPLE_RATE

        chunk_duration = self._calculate_chunk_duration(total_duration)
        chunks_info = self._create_chunks_info(audio, chunk_duration)

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = self._create_chunk_tasks(audio, chunks_info, temp_dir)
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._merge_chunk_results(chunk_results)

    def _calculate_chunk_duration(self, total_duration: float) -> float:
        """Calculate the optimal chunk duration based on concurrency and constraints."""
        if self._concurrency > 1:
            # Use concurrency to determine chunk duration
            duration = total_duration / self._concurrency
            logging.info(
                f"Using concurrency-based chunk duration: {duration:.1f}s ({self._concurrency} chunks)")
            return duration

        # Calculate based on file size limit (for large files)
        estimated_bytes_per_second = self.SAMPLE_RATE * self.BYTES_PER_SAMPLE
        duration = (self._max_file_size * self.SAFETY_MARGIN) / \
            estimated_bytes_per_second
        logging.info(f"Using size-based chunk duration: {duration:.1f}s")
        return duration

    def _create_chunks_info(self, audio, chunk_duration: float) -> Dict[str, Any]:
        """Create information about how to split the audio."""
        total_duration = len(audio) / self.SAMPLE_RATE
        num_chunks = math.ceil(total_duration / chunk_duration)

        logging.info(
            f"Splitting {total_duration:.1f}s audio into {num_chunks} chunks")
        logging.info(f"Max {self._max_concurrent_calls} concurrent API calls")

        return {
            "total_duration": total_duration,
            "chunk_duration": chunk_duration,
            "num_chunks": num_chunks
        }

    def _create_chunk_tasks(self, audio, chunks_info: Dict[str, Any], temp_dir: str) -> list:
        """Create async tasks for processing audio chunks."""
        tasks = []
        chunk_duration = chunks_info["chunk_duration"]
        total_duration = chunks_info["total_duration"]

        for i in range(chunks_info["num_chunks"]):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, total_duration)

            chunk_file = self._save_audio_chunk(
                audio, start_time, end_time, temp_dir, i)
            task = asyncio.create_task(
                self._transcribe_chunk_with_timing(chunk_file, start_time, i)
            )
            tasks.append(task)

        return tasks

    def _save_audio_chunk(self, audio, start_time: float, end_time: float,
                          temp_dir: str, chunk_index: int) -> Path:
        """Extract and save a chunk of audio to a temporary file."""
        start_sample = int(start_time * self.SAMPLE_RATE)
        end_sample = int(end_time * self.SAMPLE_RATE)
        chunk_audio = audio[start_sample:end_sample]

        chunk_file = Path(temp_dir) / f"chunk_{chunk_index:03d}.wav"
        self._write_wav_file(chunk_audio, chunk_file)
        return chunk_file

    def _write_wav_file(self, audio_data, output_path: Path) -> None:
        """Write audio data to WAV file."""
        import wave

        import numpy as np

        # Convert to 16-bit integers if needed
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)

        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.SAMPLE_RATE)
            wav_file.writeframes(audio_data.tobytes())

    def _merge_chunk_results(self, chunk_results) -> Dict[str, Any]:
        """Merge results from all chunks into a single transcription."""
        all_segments = []
        detected_language = 'en'

        for result in chunk_results:
            if isinstance(result, Exception):
                logging.error(f"Error transcribing chunk: {result}")
                continue

            if result and isinstance(result, dict) and result.get("segments"):
                all_segments.extend(result["segments"])
                if result.get("language"):
                    detected_language = result["language"]

        # Sort segments by start time
        all_segments.sort(key=lambda x: x["start"])

        logging.info(f"Successfully transcribed {len(all_segments)} segments")
        return {
            "segments": all_segments,
            "language": detected_language
        }

    async def _transcribe_chunk_with_timing(self, chunk_file: Path, start_offset: float, chunk_index: int) -> Dict[str, Any]:
        """Transcribe a single chunk and adjust timing offsets."""
        try:
            logging.info(
                f"Transcribing chunk {chunk_index}: {chunk_file.name}")
            result = await self._transcribe_single_file(chunk_file)

            # Adjust segment timings to account for chunk offset
            if result.get("segments"):
                for segment in result["segments"]:
                    segment["start"] += start_offset
                    segment["end"] += start_offset

            return result

        except Exception as e:
            logging.error(f"Error transcribing chunk {chunk_index}: {e}")
            raise
