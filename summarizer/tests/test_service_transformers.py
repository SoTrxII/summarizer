from json import dump
from os import getenv
from pathlib import Path
from typing import List, Literal

import pytest
from pydantic import BaseModel, Field
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

from summarizer.models.sentence import Sentence
from summarizer.services.transformers import NaiveTimeBasedChunker, RuptureSceneChunker

from .utils.json import read_test_data


@pytest.mark.asyncio
async def test_service_transformer_scene_chunker_naive(data_dir: Path):
    """
    OK/KO test for the NaiveTimeBasedChunker.
    """
    data_file = data_dir / "transcriptions" / "20m_sample1.json"
    sentences = read_test_data(data_file, Sentence)

    chunker = NaiveTimeBasedChunker()
    scenes = chunker.group_into_scenes(sentences)

    assert scenes is not None
    assert len(scenes) > 0


@pytest.mark.asyncio
async def test_service_transformer_scene_chunker_rupture(data_dir: Path):
    """
    OK/KO test for the RuptureSceneChunker.
    """

    data_file = data_dir / "transcriptions" / "4h_sample1_diarized.json"
    sentences = read_test_data(data_file, Sentence)

    chunker = RuptureSceneChunker("cpu")
    scenes = chunker.group_into_scenes(sentences)

    # Ensure the directory exists before writing the file
    output_dir = data_dir / "generated" / "scenes"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "4h_sample1_scenes.json", "w") as f:
        dump(scenes, f)

    assert scenes is not None
    assert len(scenes) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    getenv("SKIP_LONG_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_LONG_TESTS=true)"
)
async def test_chunking_method_comparison(data_dir: Path, azure_text_to_text_provider: AzureChatCompletion):
    """Test and compare ruptures vs naive chunking methods on topic quality.
    This is ignored by default in CI as the prompt size is quite large and requires a GPT4 like model.
    """
    data_file = data_dir / "transcriptions" / "20m_sample1.json"
    sentences = read_test_data(data_file, Sentence)

    ruptures_chunker = RuptureSceneChunker("cpu")
    naive_chunker = NaiveTimeBasedChunker()

    rupture = ruptures_chunker.group_into_scenes(sentences)
    control = naive_chunker.group_into_scenes(sentences)

    prompt = """
    You are an expert at evaluating the quality of text chunking methods based on thematic coherence and relevance.
    Given two different chunking methods applied to the same text, provide a comparative analysis of their
    effectiveness in grouping related content together.
    Here are the chunked texts from both methods:

    Method 1 (Ruptures Chunker):
    {ruptures_scenes}
    Method 2 (Naive Chunker):
    {naive_scenes}

    """

    class Result(BaseModel):
        analysis: str = Field(
            ..., description="A detailed comparative analysis of the two chunking methods focusing on thematic coherence and relevance.")
        topics_comparison: List[str] = Field(
            ..., description="Comparison of topics identified in each chunking method.")
        winner: Literal["Rupture", "Naive"] = Field(
            ..., description="The chunking method that performed better based on the analysis.")

    fmt = prompt.format(ruptures_scenes=rupture, naive_scenes=control)
    settings = AzureChatPromptExecutionSettings(temperature=0)
    settings.response_format = Result

    res = await azure_text_to_text_provider.get_text_content(fmt, settings=settings)
    assert res is not None

    comparison = Result.model_validate_json(res.text)
    print(comparison.analysis)
    assert comparison.winner != "Naive"
