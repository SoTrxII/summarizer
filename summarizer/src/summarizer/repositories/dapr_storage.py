import json
import logging
from base64 import b64decode
from typing import Any, Optional

from dapr.clients import DaprClient

from .storage import AudioRepository, SummaryRepository


class BaseDaprRepository:
    """Base class for Dapr binding repositories."""

    def __init__(self, binding_name: str):
        self.binding_name = binding_name

    async def get(self, path: str) -> Optional[bytes]:
        """Get raw data from Dapr binding."""
        try:
            with DaprClient() as client:
                result = client.invoke_binding(
                    self.binding_name,
                    "get",
                    # Note: Unfortunately, Dapr binding are not totally unified yet
                    # So, some bindings will take "filename", others "key"
                    binding_metadata={"fileName": path, "key": path}
                )
                return result.data if result.data else None
        except Exception as e:
            logging.error(
                f"Error getting data from Dapr binding '{self.binding_name}' with path '{path}': {e}")
            return None

    async def save(self, path: str, data: bytes) -> None:
        """Save raw data to Dapr binding."""
        with DaprClient() as client:
            client.invoke_binding(
                self.binding_name,
                "create",
                data=data,
                # Note: Unfortunately, Dapr binding are not totally unified yet
                # So, some bindings will take "filename", others "key"
                binding_metadata={"fileName": path, "key": path}
            )

    async def get_json(self, path: str) -> Optional[dict]:
        """Get JSON data from Dapr binding."""
        data = await self.get(path)
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    async def save_json(self, path: str, data: Any) -> None:
        """Save JSON data to Dapr binding."""
        json_data: bytes
        if hasattr(data, "model_dump_json"):
            # Pydantic model
            json_data = data.model_dump_json().encode("utf-8")
        elif hasattr(data, "model_dump"):
            # Pydantic model dict
            json_data = json.dumps(data.model_dump()).encode("utf-8")
        elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
            # List of Pydantic models
            json_data = json.dumps([item.model_dump()
                                   for item in data]).encode("utf-8")
        else:
            # Regular data
            json_data = json.dumps(data).encode("utf-8")

        await self.save(path, json_data)


class DaprAudioRepository(BaseDaprRepository, AudioRepository):
    """Dapr-based audio repository."""

    def __init__(self, binding_name: str = "audio-store"):
        super().__init__(binding_name)

    async def get(self, path: str) -> Optional[bytes]:
        data = await super().get(path)
        if not data:
            return None

        # Audio files are binary, they may be b64 encoded
        return self._maybe_base64_decode(data)

    async def get_json(self, path: str) -> Optional[dict]:
        raise NotImplementedError("Audio files are binary, not JSON")

    async def save_json(self, path: str, data: Any) -> None:
        raise NotImplementedError("Audio files are binary, not JSON")

    def _maybe_base64_decode(self, data: bytes) -> bytes:
        """Detect if data is Base64-encoded and decode if so."""
        if not data:
            return data

        try:
            # Base64 data is always ASCII
            text = data.decode("ascii")
        except UnicodeDecodeError:
            # Not even ASCII → must be raw binary
            return data

        # Length must be multiple of 4 for valid base64
        if len(text) % 4 != 0:
            return data

        try:
            return b64decode(text, validate=True)
            # Re-encode to check if it's really base64
            # if base64.b64encode(decoded).decode("ascii") == text:
            #     return decoded
        except ValueError:
            return data


class DaprSummaryRepository(BaseDaprRepository, SummaryRepository):
    """Dapr-based summary repository."""

    def __init__(self, binding_name: str = "summary-store"):
        super().__init__(binding_name)
