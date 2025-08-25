from abc import ABC, abstractmethod
from typing import Any, Optional


class StorageRepository(ABC):
    """Abstract base class for storage operations."""

    @abstractmethod
    async def get(self, path: str) -> Optional[bytes]:
        """Get raw data from storage."""
        pass

    @abstractmethod
    async def save(self, path: str, data: bytes) -> None:
        """Save raw data to storage."""
        pass

    @abstractmethod
    async def get_json(self, path: str) -> Optional[dict]:
        """Get JSON data from storage."""
        pass

    @abstractmethod
    async def save_json(self, path: str, data: Any) -> None:
        """Save JSON data to storage."""
        pass


class AudioRepository(StorageRepository):
    """Repository for audio file operations."""
    pass


class SummaryRepository(StorageRepository):
    """Repository for summaries, transcripts, and scenes."""

    def _episode_path(self, campaign_id: int, episode_id: int, filename: str) -> str:
        return f"{campaign_id}/{episode_id}/{filename}"

    def _campaign_path(self, campaign_id: int, filename: str) -> str:
        return f"{campaign_id}/{filename}"

    # Transcripts
    async def get_transcript(self, campaign_id: int, episode_id: int) -> Optional[list]:
        data = await self.get_json(self._episode_path(campaign_id, episode_id, "transcript.json"))
        return data if isinstance(data, list) else None

    async def save_transcript(self, campaign_id: int, episode_id: int, sentences: list) -> None:
        await self.save_json(self._episode_path(campaign_id, episode_id, "transcript.json"), sentences)

    # Scenes
    async def get_scenes(self, campaign_id: int, episode_id: int) -> Optional[list]:
        data = await self.get_json(self._episode_path(campaign_id, episode_id, "scenes.json"))
        return data if isinstance(data, list) else None

    async def save_scenes(self, campaign_id: int, episode_id: int, scenes: list) -> None:
        await self.save_json(self._episode_path(campaign_id, episode_id, "scenes.json"), scenes)

    # Episode summaries
    async def get_episode_summary(self, campaign_id: int, episode_id: int) -> Optional[dict]:
        return await self.get_json(self._episode_path(campaign_id, episode_id, "episode.json"))

    async def save_episode_summary(self, campaign_id: int, episode_id: int, summary: dict) -> None:
        await self.save_json(self._episode_path(campaign_id, episode_id, "episode.json"), summary)

    # Campaign summaries
    async def get_campaign_summary(self, campaign_id: int) -> Optional[dict]:
        return await self.get_json(self._campaign_path(campaign_id, "campaign.json"))

    async def save_campaign_summary(self, campaign_id: int, summary: dict) -> None:
        await self.save_json(self._campaign_path(campaign_id, "campaign.json"), summary)
