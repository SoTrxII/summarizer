import logging
from json import dumps
from os import getenv
from pathlib import Path

import pytest
from deepeval.metrics import SummarizationMetric
from deepeval.models import AzureOpenAIModel
from deepeval.test_case import LLMTestCase
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

from summarizer.models.scene import Scene
from summarizer.models.sentence import Sentence
from summarizer.services.summaries.models import EpisodeSummary, SceneSummary
from summarizer.services.summaries.summarizer import Summarizer
from summarizer.utils.naming import get_standardized_filenames

from .utils.json import read_test_data, write_test_data

# Base names for test data
base_names = ["1m_sample1", "1m_sample2"]


@pytest.mark.parametrize("base_name", base_names, ids=["part1", "part2"])
@pytest.mark.asyncio
async def test_service_summaries_scene(base_name: str, data_dir: Path, summarizer: Summarizer):
    scenes_file, scene_summaries_file, _ = get_standardized_filenames(
        base_name)

    sample_scenes = read_test_data(data_dir / "scenes" / scenes_file, Scene)
    if len(sample_scenes) == 0:
        raise ValueError("No scenes found in the sample file")

    # Generate summaries
    summaries = []
    for i, current in enumerate(sample_scenes):
        previous = summaries[-1] if i > 0 else None
        summaries.append((await summarizer.scene(current, previous_summary=previous)).model_dump())

    # Write summaries
    write_test_data(data_dir / "generated" / "summaries" /
                    scene_summaries_file, summaries, ensure_ascii=False)
    # write_test_data(data_dir / "summaries" /
    #                 scene_summaries_file, summaries, ensure_ascii=False)

    assert all(summary is not None for summary in summaries)
    logging.info(f"Summarization results: {summaries}")


@pytest.mark.parametrize("base_name", base_names, ids=["part1", "part2"])
@pytest.mark.asyncio
async def test_service_summaries_episode(base_name: str, data_dir: Path, summarizer: Summarizer):
    _, scene_summaries_file, episode_summary_file = get_standardized_filenames(
        base_name)

    # Read scene summaries
    sample_scenes = read_test_data(
        data_dir / "summaries" / scene_summaries_file, SceneSummary)
    if len(sample_scenes) == 0:
        raise ValueError("No summaries found in the sample file")

    # Generate episode summary
    summary = await summarizer.episode(sample_scenes)

    # Write episode summary
    write_test_data(data_dir / "generated" / "summaries" /
                    episode_summary_file, summary, ensure_ascii=False)
    # write_test_data(data_dir / "summaries" /
    #                 episode_summary_file, summary, ensure_ascii=False)
    assert summary is not None
    logging.info(f"Summarization result: {summary}")


@pytest.mark.asyncio
async def test_service_summaries_campaign(data_dir: Path, summarizer: Summarizer):
    # Read episode summaries
    sample_episodes = []
    for base_name in base_names:
        _, _, episode_summary_file = get_standardized_filenames(base_name)
        episodes = read_test_data(
            data_dir / "summaries" / episode_summary_file, EpisodeSummary)
        sample_episodes.extend(episodes)

    if len(sample_episodes) == 0:
        raise ValueError("No episode summaries found in the sample files")

    # Generate campaign summary
    summary = await summarizer.campaign(sample_episodes)

    # Write campaign summary
    write_test_data(data_dir / "generated" / "summaries" /
                    "campaign_summary.json", summary, ensure_ascii=False)
    # write_test_data(data_dir / "summaries" /
    #                 "campaign_summary.json", summary, ensure_ascii=False)

    assert summary is not None
    logging.info(f"Campaign summarization result: {summary}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    getenv("SKIP_LONG_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_LONG_TESTS=true)"
)
async def test_service_summaries_scene_quality(data_dir: Path, summarizer: Summarizer, deepeval_model: AzureOpenAIModel, azure_text_to_text_provider: AzureChatCompletion):
    """
    This test ensures that character information is correctly mapped between scenes and summaries.
    """
    THRESHOLD = 0.5

    # Input
    scenes_file, _, _ = get_standardized_filenames("5m_sample1")
    sample_scenes = read_test_data(data_dir / "scenes" / scenes_file, Scene)
    if len(sample_scenes) == 0:
        raise ValueError("No scenes found in the sample file")

    # Summarize
    summary = await summarizer.scene(sample_scenes[0])
    input = dumps(sample_scenes[0])

    # Evaluate
    test_case = LLMTestCase(input=input, actual_output=summary.human_summary)
    metric = SummarizationMetric(model=deepeval_model, threshold=THRESHOLD)
    metric.measure(test_case)

    assert metric.score is not None and metric.score >= THRESHOLD, "\n".join([
        "Reason: " + str(metric.reason),
        "Details: " + str(metric.score_breakdown),
        "Output: " + summary.human_summary
    ])


@pytest.mark.asyncio
@pytest.mark.skipif(
    getenv("SKIP_LONG_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_LONG_TESTS=true)"
)
async def test_service_summaries_episode_quality(data_dir: Path, summarizer: Summarizer, deepeval_model: AzureOpenAIModel, azure_text_to_text_provider: AzureChatCompletion):
    """
    This test compares the episode summary generated by the summarizer
    against a control summary generated by a naive approach using the same LLM.
    This is ignored by default in CI as the prompt size is quite large and requires a GPT4 like model.
    """
    ###########
    # Naive summarization
    ##########
    data_file = data_dir / "transcriptions" / "1h_sample1_diarized.json"
    sentences = read_test_data(data_file, Sentence)
    input = dumps(sentences)

    prompt = """
    You are a helpful assistant that summarizes the content of a tabletop role-playing game session.
    Summarize this episode based on the episode transcription below.
    Transcription:
    {input}
    Provide a concise summary that captures the main events, characters, and plot developments in French.
    Keep the summary to a few paragraphs.
    """

    fmt = prompt.format(input=input)
    settings = AzureChatPromptExecutionSettings(temperature=0)
    control_summary = await azure_text_to_text_provider.get_text_content(fmt, settings=settings)
    assert control_summary is not None

    control_tc = LLMTestCase(input=input, actual_output=control_summary.text)
    control_metric = SummarizationMetric(model=deepeval_model)
    control_metric.measure(control_tc)

    ###########
    # Summarizer
    ##########
    scenes_file, _, _ = get_standardized_filenames("1h_sample1")
    sample_scenes = read_test_data(data_dir / "scenes" / scenes_file, Scene)
    if len(sample_scenes) == 0:
        raise ValueError("No scenes found in the sample file")

    scenes_summaries = [await summarizer.scene(scene) for scene in sample_scenes]
    episode_summary = await summarizer.episode(scenes_summaries)
    # campaign_summary = await summarizer.campaign([episode_summary])

    sum_tc = LLMTestCase(
        input=input, actual_output=episode_summary.human_summary)
    sum_metric = SummarizationMetric(model=deepeval_model)
    sum_metric.measure(sum_tc)

    ###########
    # Comparison
    ##########
    assert sum_metric.score is not None and control_metric.score is not None
    assert sum_metric.score >= control_metric.score, "\n".join([
        f"Summarizer score: {sum_metric.score} (reason: {sum_metric.reason}, details: {sum_metric.score_breakdown})",
        f"Control score: {control_metric.score} (reason: {control_metric.reason}, details: {control_metric.score_breakdown})",
        "Output: " + episode_summary.human_summary
    ])
