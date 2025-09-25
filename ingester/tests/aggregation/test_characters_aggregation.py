from summarizer.services.summaries.models import Character


def test_aggregate_characters_empty_list():
    """Test aggregating an empty list returns empty list."""
    result = Character.aggregate([])
    assert result == []


def test_aggregate_characters_single_character():
    """Test aggregating a single character returns the same character."""
    char = Character(
        character_id="test_char",
        name="Test Character",
        description="A test character"
    )

    result = Character.aggregate([char])
    assert len(result) == 1
    assert result[0].name == "Test Character"


def test_aggregate_characters_same_character_id():
    """Test aggregating characters with same character_id merges them."""
    char1 = Character(
        character_id="aragorn",
        name="Aragorn",
        description="A ranger",
        aliases=["Strider"]
    )
    char2 = Character(
        character_id="aragorn",
        name="Aragorn",
        description="A ranger and rightful king",
        aliases=["King Elessar"]
    )

    result = Character.aggregate([char1, char2])

    # Should merge into a single character
    assert len(result) == 1
    merged_char = result[0]

    # Should combine aliases
    assert "Strider" in merged_char.aliases
    assert "King Elessar" in merged_char.aliases

    # Should use the more detailed description
    assert merged_char.description is not None
    assert "rightful king" in merged_char.description
