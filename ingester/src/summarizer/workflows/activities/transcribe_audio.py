"""
Transcribe audio activity for the summarization workflow.
"""

import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.sentence import Sentence
from summarizer.models.workflow import AudioWorkflowInput
from summarizer.repositories.storage import AudioRepository, SummaryRepository
from summarizer.services.speech_to_text import SpeechToText
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def transcribe_audio(
    _: WorkflowActivityContext,
    input: AudioWorkflowInput,
    speech_to_text: SpeechToText = Provide[Container.speech_to_text],
    audio_repo: AudioRepository = Provide[Container.audio_repository],
    summary_repo: SummaryRepository = Provide[Container.summary_repository]
) -> List[Sentence]:
    """
    Transcribe an audio file on a remote
    """

    async def run():
        with NamedTemporaryFile(suffix=".ogg") as tmp:
            # Get audio data
            audio_data = await audio_repo.get(input["audio_file_path"])
            if audio_data:
                tmp.write(audio_data)

                # Transcribe
                sentences = await speech_to_text.transcribe(Path(tmp.name), diarize=True)

                # Save transcript
                await summary_repo.save_transcript(
                    input["campaign_id"],
                    input["episode_id"],
                    sentences
                )

                return sentences
            else:
                raise ValueError(
                    f"Audio file not found: {input['audio_file_path']}")

    return asyncio.run(run())
