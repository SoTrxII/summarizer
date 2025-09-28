from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Notification(BaseModel):
    campaign_id: int
    episode_id: int

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class SummaryAvailable(Notification):
    """
    Notification sent when new episode summary is available
    """
    summary: str
    episode_key: str
    campaign_key: str