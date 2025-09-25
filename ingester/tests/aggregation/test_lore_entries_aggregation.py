from summarizer.services.summaries.models import LoreEntry


def test_aggregate_empty_list():
    """Test aggregating an empty list returns empty list."""
    result = LoreEntry.aggregate([])
    assert result == []


def test_aggregate_single_lore():
    """Test aggregating a single lore entry returns the same entry."""
    lore = LoreEntry(
        lore_id="test_lore",
        title="Test Lore",
        description="A piece of lore",
        from_episode="1"
    )

    result = LoreEntry.aggregate([lore])
    assert len(result) == 1
    assert result[0].description == "A piece of lore"


def test_aggregate_same_lore_id():
    """Test aggregating lore entries with same lore_id merges them."""
    lore1 = LoreEntry(
        lore_id="ancient_artifact",
        title="Ancient Artifact",
        description="A mysterious ancient artifact",
        from_episode="1"
    )
    lore2 = LoreEntry(
        lore_id="ancient_artifact",
        title="Ancient Artifact Details",
        description="A mysterious ancient artifact with magical properties",
        from_episode="2"
    )

    result = LoreEntry.aggregate([lore1, lore2])

    # Should merge into a single entry
    assert len(result) == 1
    merged_lore = result[0]

    # Should use the more detailed description
    assert len(merged_lore.description) > len(lore1.description)
    # Should use the earlier episode
    assert merged_lore.from_episode == "1"


def test_aggregate_different_lore():
    """Test aggregating different lore entries keeps them separate."""
    lore1 = LoreEntry(
        lore_id="lore1",
        title="Ancient Dragon",
        description="The ancient dragon sleeps",
        from_episode="1"
    )
    lore2 = LoreEntry(
        lore_id="lore2",
        title="Wizard's Tower",
        description="The wizard's tower stands tall",
        from_episode="2"
    )

    result = LoreEntry.aggregate([lore1, lore2])

    # Should keep separate
    assert len(result) == 2
