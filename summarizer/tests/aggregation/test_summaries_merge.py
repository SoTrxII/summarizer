from summarizer.services.summaries.models import (
    Character,
    Event,
    LoreEntry,
    Summary,
    Timestamps,
)


def test_merge_empty_list():
    """Test merging an empty list returns empty summary."""
    result = Summary.merge([])

    assert result.human_summary == ""
    assert result.schema_version == "v1.0"
    assert result.timestamps.start == 0
    assert result.timestamps.end == 0
    assert result.events == []
    assert result.npcs == []
    assert result.player_characters == []
    assert result.world_lore == []


def test_merge_single_summary():
    """Test merging a single summary returns the same summary with some modifications."""
    summary = Summary(
        schema_version="xx",
        human_summary="A single scene",
        timestamps=Timestamps(start=10, end=20),
        events=[
            Event(
                timestamps=Timestamps(start=11, end=12),
                description="Something happened",
                actors=["char1"],
                scene_impact=""
            )
        ],
        npcs=[
            Character(character_id="npc1", name="NPC One", description="bald")
        ],
        player_characters=[
            Character(character_id="pc1", name="Player One",
                      description="less bald")
        ],
        world_lore=[
            LoreEntry(
                lore_id="lore1",
                description="Ancient lore",
                from_episode="1",
                title="lore"
            )
        ]
    )

    result = Summary.merge([summary])

    # Should preserve the content but may aggregate duplicates
    assert result.human_summary != ""
    assert result.timestamps.start == 10
    assert result.timestamps.end == 20
    assert len(result.events) >= 1
    assert len(result.npcs) >= 1
    assert len(result.player_characters) >= 1
    assert len(result.world_lore) >= 1


def test_merge_multiple_summaries():
    """Test merging multiple summaries combines all data."""
    summary1 = Summary(
        schema_version="xx",
        human_summary="First scene",
        timestamps=Timestamps(start=0, end=10),
        events=[
            Event(
                timestamps=Timestamps(start=1, end=2),
                description="First event",
                actors=["char1"],
                scene_impact=""
            )
        ],
        npcs=[
            Character(character_id="npc1", name="NPC One", description="")
        ],
        player_characters=[
            Character(character_id="pc1",
                      name="Player with a sword", description="")
        ],
        world_lore=[
            LoreEntry(
                lore_id="lore1",
                description="First lore",
                from_episode="1",
                title="lore"
            )
        ]
    )

    summary2 = Summary(
        schema_version="xx",
        human_summary="Second scene",
        timestamps=Timestamps(start=10, end=20),
        events=[
            Event(
                timestamps=Timestamps(start=11, end=12),
                description="Second event",
                actors=["char2"],
                scene_impact=""
            )
        ],
        npcs=[
            Character(character_id="npc2", name="NPC Two", description="")
        ],
        player_characters=[
            Character(character_id="pc2",
                      name="Player with an axe", description="")
        ],
        world_lore=[
            LoreEntry(
                lore_id="lore2",
                description="Second lore",
                from_episode="2",
                title="lore2"
            )
        ]
    )

    result = Summary.merge([summary1, summary2])

    # Should span the entire time range
    assert result.timestamps.start == 0
    assert result.timestamps.end == 20

    # Should contain elements from both summaries
    assert len(result.events) >= 2
    assert len(result.npcs) >= 2
    assert len(result.player_characters) >= 2
    assert len(result.world_lore) >= 2
