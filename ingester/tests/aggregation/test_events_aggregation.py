from summarizer.services.summaries.models import Event, Timestamps


def test_aggregate_events_empty_list():
    """Test aggregating an empty list returns empty list."""
    result = Event.aggregate([])
    assert result == []


def test_aggregate_events_single_event():
    """Test aggregating a single event returns the same event."""
    event = Event(
        timestamps=Timestamps(start=10, end=20),
        description="Single event",
        actors=["char1"],
        scene_impact=""
    )

    result = Event.aggregate([event])
    assert len(result) == 1
    assert result[0].description == "Single event"


def test_aggregate_events_non_overlapping_events():
    """Test aggregating non-overlapping events keeps them separate."""
    event1 = Event(
        timestamps=Timestamps(start=0, end=10),
        description="First event",
        actors=["char1"],
        scene_impact=""
    )
    event2 = Event(
        timestamps=Timestamps(start=20, end=30),
        description="Second event",
        actors=["char2"],
        scene_impact=""
    )

    result = Event.aggregate([event1, event2])
    assert len(result) == 2


def test_aggregate_events_overlapping_similar_events():
    """Test aggregating overlapping events with similar descriptions merges them."""
    event1 = Event(
        timestamps=Timestamps(start=0, end=15),
        description="Combat begins",
        actors=["char1"],
        scene_impact=""
    )
    event2 = Event(
        timestamps=Timestamps(start=10, end=25),
        description="Combat starts",
        actors=["char2"],
        scene_impact=""
    )

    result = Event.aggregate([event1, event2], similarity_threshold=0.6)

    # Should merge into a single event due to overlap and similarity
    assert len(result) == 1
    merged_event = result[0]

    # Should span the combined time range
    assert merged_event.timestamps.start == 0
    assert merged_event.timestamps.end == 25

    # Should combine actors
    assert "char1" in merged_event.actors
    assert "char2" in merged_event.actors


def test_aggregate_events_overlapping_different_events():
    """Test aggregating overlapping events with different descriptions keeps them separate."""
    event1 = Event(
        timestamps=Timestamps(start=0, end=15),
        description="Combat begins",
        actors=["char1"],
        scene_impact=""
    )
    event2 = Event(
        timestamps=Timestamps(start=10, end=25),
        description="Magic spell cast",
        actors=["char2"],
        scene_impact=""
    )

    result = Event.aggregate([event1, event2], similarity_threshold=0.8)

    # Should keep separate due to low similarity despite overlap
    assert len(result) == 2
