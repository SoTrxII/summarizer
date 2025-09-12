#!/usr/bin/env python3
"""
Simple test script to verify the _aggregate_scenes function works correctly.
"""

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List


# Mock the models to avoid dependencies
@dataclass
class Timestamps:
    start: float
    end: float


@dataclass
class Event:
    timestamps: Timestamps
    description: str
    actors: List[str]
    scene_impact: str = None


@dataclass
class LoreEntry:
    lore_id: str
    title: str
    description: str
    from_episode: str


@dataclass
class Character:
    character_id: str
    name: str
    aliases: List[str]
    description: str = None


@dataclass
class SceneSummary:
    timestamps: Timestamps
    human_summary: str
    events: List[Event]
    world_lore: List[LoreEntry]
    player_characters: List[Character]
    npcs: List[Character]

# Copy the aggregation logic here for testing


class TestSummarizer:
    @staticmethod
    def _aggregate_scenes(scenes: List[SceneSummary]) -> dict:
        """Test version of the aggregate function"""
        if not scenes:
            return {
                "events": [],
                "world_lore": [],
                "player_characters": [],
                "npcs": []
            }

        start_time = min(scene.timestamps.start for scene in scenes)
        end_time = max(scene.timestamps.end for scene in scenes)

        aggregated_events = TestSummarizer._aggregate_events(scenes)
        aggregated_lore = TestSummarizer._aggregate_lore(scenes)
        aggregated_player_characters = TestSummarizer._aggregate_characters([
            char for scene in scenes for char in scene.player_characters
        ])
        aggregated_npcs = TestSummarizer._aggregate_characters([
            char for scene in scenes for char in scene.npcs
        ])

        return {
            "timestamps": Timestamps(start=start_time, end=end_time),
            "events": aggregated_events,
            "world_lore": aggregated_lore,
            "player_characters": aggregated_player_characters,
            "npcs": aggregated_npcs
        }

    @staticmethod
    def _aggregate_events(scenes: List[SceneSummary]) -> List[Event]:
        all_events = []
        for scene in scenes:
            all_events.extend(scene.events)

        if not all_events:
            return []

        all_events.sort(key=lambda e: e.timestamps.start)
        aggregated = []
        similarity_threshold = 0.85

        for event in all_events:
            merged = False

            for existing in aggregated:
                if TestSummarizer._events_overlap(event, existing):
                    similarity = SequenceMatcher(None, event.description.lower(),
                                                 existing.description.lower()).ratio()

                    if similarity >= similarity_threshold:
                        TestSummarizer._merge_events(existing, event)
                        merged = True
                        break

            if not merged:
                aggregated.append(event)

        return aggregated

    @staticmethod
    def _aggregate_lore(scenes: List[SceneSummary]) -> List[LoreEntry]:
        all_lore = []
        for scene in scenes:
            all_lore.extend(scene.world_lore)

        if not all_lore:
            return []

        aggregated = []
        similarity_threshold = 0.9

        for lore in all_lore:
            merged = False

            for existing in aggregated:
                if existing.lore_id == lore.lore_id:
                    if lore.description and len(lore.description) > len(existing.description):
                        existing.description = lore.description
                    merged = True
                    break

            if not merged:
                for existing in aggregated:
                    similarity = SequenceMatcher(None, lore.description.lower(),
                                                 existing.description.lower()).ratio()

                    if similarity >= similarity_threshold:
                        if lore.title and not existing.title:
                            existing.title = lore.title
                        if len(lore.description) > len(existing.description):
                            existing.description = lore.description
                        merged = True
                        break

            if not merged:
                aggregated.append(lore)

        return aggregated

    @staticmethod
    def _aggregate_characters(characters: List[Character]) -> List[Character]:
        if not characters:
            return []

        aggregated = []
        similarity_threshold = 0.8

        for char in characters:
            merged = False

            for existing in aggregated:
                if existing.character_id == char.character_id:
                    TestSummarizer._merge_characters(existing, char)
                    merged = True
                    break

            if not merged:
                for existing in aggregated:
                    name_similarity = SequenceMatcher(None, char.name.lower(),
                                                      existing.name.lower()).ratio()

                    name_in_aliases = (char.name.lower() in [alias.lower() for alias in existing.aliases] or
                                       existing.name.lower() in [alias.lower() for alias in char.aliases])

                    if name_similarity >= similarity_threshold or name_in_aliases:
                        TestSummarizer._merge_characters(existing, char)
                        merged = True
                        break

            if not merged:
                aggregated.append(char)

        return aggregated

    @staticmethod
    def _events_overlap(event1: Event, event2: Event) -> bool:
        return not (event1.timestamps.end <= event2.timestamps.start or
                    event2.timestamps.end <= event1.timestamps.start)

    @staticmethod
    def _merge_events(existing: Event, new: Event) -> None:
        existing.timestamps.start = min(
            existing.timestamps.start, new.timestamps.start)
        existing.timestamps.end = max(
            existing.timestamps.end, new.timestamps.end)

        for actor in new.actors:
            if actor not in existing.actors:
                existing.actors.append(actor)

        if new.scene_impact and new.scene_impact not in (existing.scene_impact or ""):
            if existing.scene_impact:
                existing.scene_impact += f" | {new.scene_impact}"
            else:
                existing.scene_impact = new.scene_impact

        if len(new.description) > len(existing.description):
            existing.description = new.description

    @staticmethod
    def _merge_characters(existing: Character, new: Character) -> None:
        for alias in new.aliases:
            if alias not in existing.aliases and alias.lower() != existing.name.lower():
                existing.aliases.append(alias)

        if new.name.lower() != existing.name.lower() and new.name not in existing.aliases:
            existing.aliases.append(new.name)

        if new.description and (not existing.description or len(new.description) > len(existing.description)):
            existing.description = new.description


def convert_data(scene_data):
    """Convert JSON data to our test objects"""
    # Convert timestamps
    ts = Timestamps(start=scene_data["timestamps"]
                    ["start"], end=scene_data["timestamps"]["end"])

    # Convert events
    events = []
    for event_data in scene_data.get("events", []):
        event_ts = Timestamps(start=event_data["timestamps"].get("start", 0),
                              end=event_data["timestamps"]["end"])
        event = Event(
            timestamps=event_ts,
            description=event_data["description"],
            actors=event_data.get("actors", []),
            scene_impact=event_data.get("scene_impact")
        )
        events.append(event)

    # Convert lore
    lore = []
    for lore_data in scene_data.get("world_lore", []):
        lore_entry = LoreEntry(
            lore_id=lore_data["lore_id"],
            title=lore_data.get("title"),
            description=lore_data["description"],
            from_episode=lore_data["provenance_episode"]
        )
        lore.append(lore_entry)

    # Convert characters
    def convert_chars(char_list):
        chars = []
        for char_data in char_list:
            char = Character(
                character_id=char_data["character_id"],
                name=char_data["name"],
                aliases=char_data.get("aliases", []),
                description=char_data.get("description")
            )
            chars.append(char)
        return chars

    player_characters = convert_chars(scene_data.get("player_characters", []))
    npcs = convert_chars(scene_data.get("npcs", []))

    return SceneSummary(
        timestamps=ts,
        human_summary=scene_data["human_summary"],
        events=events,
        world_lore=lore,
        player_characters=player_characters,
        npcs=npcs
    )


def test_with_sample_data():
    """Test the aggregate function with the provided scenes_summaries.json data."""

    # Load the sample data
    with open('/workspaces/summarizer/summarizer/data/generated/5/1/scenes_summaries.json', 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)

    # Convert to our test objects
    scenes = [convert_data(scene_data) for scene_data in scenes_data]

    print(f"Loaded {len(scenes)} scenes")
    print(
        f"Time range: {scenes[0].timestamps.start:.1f}s - {scenes[-1].timestamps.end:.1f}s")

    # Test the aggregation function
    result = TestSummarizer._aggregate_scenes(scenes)

    # Print results
    print("\nAggregation Results:")
    print(
        f"- Overall timestamps: {result['timestamps'].start:.1f}s - {result['timestamps'].end:.1f}s")
    print(f"- Total events: {len(result['events'])}")
    print(f"- Total lore entries: {len(result['world_lore'])}")
    print(f"- Total player characters: {len(result['player_characters'])}")
    print(f"- Total NPCs: {len(result['npcs'])}")

    # Show some details
    print("\nPlayer Characters:")
    for char in result['player_characters']:
        aliases_str = f" (aliases: {', '.join(char.aliases)})" if char.aliases else ""
        print(f"  - {char.name}{aliases_str}")

    print("\nNPCs:")
    for char in result['npcs']:
        aliases_str = f" (aliases: {', '.join(char.aliases)})" if char.aliases else ""
        print(f"  - {char.name}{aliases_str}")

    print("\nLore Entries:")
    for lore in result['world_lore']:
        print(f"  - {lore.lore_id}: {lore.title or 'No title'}")

    print("\nEvents (first 3):")
    for i, event in enumerate(result['events'][:3]):
        actors_str = f" [Actors: {', '.join(event.actors)}]" if event.actors else ""
        print(
            f"  {i+1}. [{event.timestamps.start:.1f}s-{event.timestamps.end:.1f}s]{actors_str}: {event.description[:100]}...")


if __name__ == "__main__":
    test_with_sample_data()
