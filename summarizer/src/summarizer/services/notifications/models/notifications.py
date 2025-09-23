from typing import TypedDict


class Notification(TypedDict):
    campaign_id: int
    episode_id: int


class SummaryAvailable(Notification):
    """
    Notification sent when new episode summary is available
    """
    # The key for the episode summary in the storage
    episode_summary_key: str
    # The key for the campaign summary in the storage
    campaign_summary_key: str
