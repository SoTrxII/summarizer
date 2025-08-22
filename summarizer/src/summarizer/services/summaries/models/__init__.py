"""
Standardized models for RPG session summaries.

This module provides consistent data structures for summarizing RPG content
at different levels: scenes, episodes, and campaigns.
"""

from .base_models import (
    CharacterUpdate,
    NPCInfo,
    ItemOrClue,
    OpenThread,
    Timestamps
)
from .scene_summary import PlayerAction, SceneSummary
from .episode_summary import EpisodeSummary
from .campaign_summary import StoryArc, CampaignSummary

__all__ = [
    # Base models
    "CharacterUpdate",
    "NPCInfo", 
    "ItemOrClue",
    "OpenThread",
    "Timestamps",
    # Scene models
    "PlayerAction",
    "SceneSummary",
    # Episode models
    "EpisodeSummary",
    # Campaign models
    "StoryArc",
    "CampaignSummary",
]
