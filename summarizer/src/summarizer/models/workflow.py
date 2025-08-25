"""
Models for workflow inputs and outputs.
"""
from typing import List, TypedDict


class WorkflowInput(TypedDict):
    """Base input parameters for workflows."""
    campaign_id: int
    episode_id: int


class AudioWorkflowInput(WorkflowInput):
    """Input parameters for the audio-to-summary workflow."""
    audio_file_path: str


class SummarizeEpisodeActivityInput(WorkflowInput):
    """Input for the summarize episode activity."""
    # Note : This can't be properly typed as scenes summaries are pydantic objets
    # and these aren't serializable
    scenes_summaries: List[dict]


class SummarizeCampaignActivityInput(WorkflowInput):
    """Input for the summarize campaign activity."""
    # Note : This can't be properly typed as scenes summaries are pydantic objets
    # and these aren't serializable
    episode: dict


class WorkflowStartResponse(TypedDict):
    """Response when starting a workflow."""
    workflow_id: str
    message: str
