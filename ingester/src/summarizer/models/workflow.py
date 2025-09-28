"""
Models for workflow inputs and outputs.
"""
from typing import List, TypedDict

from summarizer.models.scene import Scene


class WorkflowInput(TypedDict):
    """Base input parameters for workflows."""
    campaign_id: int
    episode_id: int
    # True if the episode is a One Shot.
    # A One Shot is a standalone episode that doesn't belong to a series.
    # It means that it doesn't need any previous context to be understood.
    is_one_shot: bool


class AudioWorkflowInput(WorkflowInput):
    """Input parameters for the audio-to-summary workflow."""
    audio_file_path: str


class SummarizeScenesActivityInput(WorkflowInput):
    """Input for the summarize episode activity."""
    # Note : This can't be properly typed as scenes summaries are pydantic objets
    # and these aren't serializable
    scenes: List[Scene]


class SummarizeEpisodeActivityInput(WorkflowInput):
    """Input for the summarize episode activity."""
    # Note : This can't be properly typed as scenes summaries are pydantic objets
    # and these aren't serializable
    scenes_summaries: List[dict]


class SummarizeCampaignActivityInput(WorkflowInput):
    """Input for the summarize campaign activity."""
    # Note : This can't be properly typed as scenes summaries are pydantic objets
    # and these aren't serializable
    episode_summary: dict


class NotifySummaryAvailableActivityInput(WorkflowInput):
    """Input for the notify summary available activity."""
    # Note : This can't be properly typed as episode summary is a pydantic object
    # and these aren't serializable
    episode_summary: dict


class WorkflowStartResponse(TypedDict):
    """Response when starting a workflow."""
    workflow_id: str
    message: str
