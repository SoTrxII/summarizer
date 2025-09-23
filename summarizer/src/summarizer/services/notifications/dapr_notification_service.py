import logging
from json import dumps

from dapr.clients import DaprClient

from .models import Notification, SummaryAvailable


class DaprNotificationService:
    """Dapr-based notification service that publishes messages to a pub/sub broker."""

    def __init__(self, pubsub_name: str = "notification-pubsub", topic: str = "notifications"):
        """
        Initialize the Dapr notification service.

        Args:
            pubsub_name: The name of the Dapr pub/sub component. If None, notifications are disabled.
        """
        self.pubsub_name = pubsub_name
        self.topic = topic
        self.logger = logging.getLogger(__name__)

    async def summary_available(self, payload: SummaryAvailable) -> bool:
        """
        Advertise that a new set of summaries is available.
        Args:

        """
        return await self.__send(self.topic, payload)

    async def __send(self, topic: str, notification: Notification) -> bool:
        """
        Send a generic notification message to a specific topic.

        Args:
            topic: The topic/channel to send the notification to
            notification: The notification message to send

        Returns:
            True if the notification was sent successfully, False otherwise
        """

        try:
            with DaprClient() as client:
                self.logger.info(
                    f"Sending notification to topic '{topic}' on pubsub '{self.pubsub_name}'"
                )

                client.publish_event(
                    pubsub_name=self.pubsub_name,
                    topic_name=topic,
                    data=dumps(notification)
                )

                self.logger.info(
                    f"Successfully sent notification to topic '{topic}'"
                )
                return True

        except Exception as e:
            self.logger.error(
                f"Failed to send notification to topic '{topic}': {e}"
            )
            return False
