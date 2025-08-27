import logging
from pathlib import Path

import pytest

from summarizer.models.scene import Scene
from summarizer.services.summaries.models.episode_summary import EpisodeSummary
from summarizer.services.summaries.models.scene_summary import SceneSummary
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
    write_test_data(data_dir / "summaries" /
                    episode_summary_file, summary, ensure_ascii=False)

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
    write_test_data(data_dir / "summaries" /
                    "campaign_summary.json", summary, ensure_ascii=False)

    assert summary is not None
    logging.info(f"Campaign summarization result: {summary}")
