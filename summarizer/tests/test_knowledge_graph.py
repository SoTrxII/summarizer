"""Tests for the LightRAG knowledge graph service."""

from pathlib import Path

import pytest

from summarizer.services.knowledge_graph import KnowledgeGraph
from summarizer.services.summaries.models.scene_summary import SceneSummary
from summarizer.utils.naming import get_standardized_filenames

from .utils.json import read_test_data

base_names = ["1m_sample1", "1m_sample2"]


@pytest.mark.asyncio
@pytest.mark.skip(reason="Manual testing only. Requires the Lighrag server to be started")
@pytest.mark.parametrize("base_name", base_names, ids=["part1", "part2"])
async def test_index_scenes(base_name: str, knowledge_graph: KnowledgeGraph, data_dir: Path):
    _, scene_summaries_file, _ = get_standardized_filenames(base_name)

    # Read scene summaries
    sample_scenes = read_test_data(
        data_dir / "summaries" / scene_summaries_file, SceneSummary)
    if len(sample_scenes) == 0:
        raise ValueError("No summaries found in the sample file")

    res = await knowledge_graph.index_scenes(1, 1, sample_scenes)

    assert res is not None
    assert isinstance(res, list)
    assert all(isinstance(item, dict) for item in res)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Manual testing only. Requires the Lighrag server to be started")
async def test_query(knowledge_graph: KnowledgeGraph):

    res = await knowledge_graph.query("What are the npc of the story ? ", 1, 1)

    assert res is not None
    assert len(res) > 0
