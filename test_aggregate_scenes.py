#!/usr/bin/env python3
"""
Simple test script to verify the _aggregate_scenes function works correctly.
"""

from summarizer.services.summaries.summarizer import Summarizer
from summarizer.services.summaries.models.scene_summary import SceneSummary
import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, '/workspaces/summarizer/summarizer/src')


def test_with_sample_data():
    """Test the aggregate function with the provided scenes_summaries.json data."""

    # Load the sample data
    with open('/workspaces/summarizer/summarizer/data/generated/5/1/scenes_summaries.json', 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)

    # Convert to SceneSummary objects
    scenes = [SceneSummary.model_validate(
        scene_data) for scene_data in scenes_data]

    print(f"Loaded {len(scenes)} scenes")
    print(
        f"Time range: {scenes[0].timestamps.start:.1f}s - {scenes[-1].timestamps.end:.1f}s")

    # Test the aggregation function
    result = Summarizer._aggregate_scenes(scenes)

    # Print results
    print(f"\nAggregation Results:")
    print(
        f"- Overall timestamps: {result['timestamps'].start:.1f}s - {result['timestamps'].end:.1f}s")
    print(f"- Total events: {len(result['events'])}")
    print(f"- Total lore entries: {len(result['world_lore'])}")
    print(f"- Total player characters: {len(result['player_characters'])}")
    print(f"- Total NPCs: {len(result['npcs'])}")

    # Show some details
    print(f"\nPlayer Characters:")
    for char in result['player_characters']:
        aliases_str = f" (aliases: {', '.join(char.aliases)})" if char.aliases else ""
        print(f"  - {char.name}{aliases_str}")

    print(f"\nNPCs:")
    for char in result['npcs']:
        aliases_str = f" (aliases: {', '.join(char.aliases)})" if char.aliases else ""
        print(f"  - {char.name}{aliases_str}")

    print(f"\nLore Entries:")
    for lore in result['world_lore']:
        print(f"  - {lore.lore_id}: {lore.title or 'No title'}")

    print(f"\nEvents (first 3):")
    for i, event in enumerate(result['events'][:3]):
        actors_str = f" [Actors: {', '.join(event.actors)}]" if event.actors else ""
        print(
            f"  {i+1}. [{event.timestamps.start:.1f}s-{event.timestamps.end:.1f}s]{actors_str}: {event.description[:100]}...")


if __name__ == "__main__":
    test_with_sample_data()
