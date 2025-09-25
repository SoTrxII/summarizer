from typing import Protocol

from .models import SummaryAvailable


class NotificationService(Protocol):
    """
    A notification service that sends completion notifications to a message broker.
    """

    async def summary_available(self, payload: SummaryAvailable) -> bool:
        """
        Send a generic notification message to a specific topic.

        Args:
            topic: The topic/channel to send the notification to
            notification: The notification message to send

        Returns:
            True if the notification was sent successfully, False otherwise
        """
        ...
