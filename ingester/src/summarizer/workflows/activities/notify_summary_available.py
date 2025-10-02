"""
Notify summary available activity for the summarization workflow.
"""

import asyncio
import logging

from dapr.ext.workflow import WorkflowActivityContext
from dependency_injector.wiring import Provide, inject

from summarizer.container import Container
from summarizer.models.workflow import NotifySummaryAvailableActivityInput
from summarizer.services.notifications import DaprNotificationService, SummaryAvailable
from summarizer.services.summaries.models import EpisodeSummary
from summarizer.utils.telemetry import span

from ..runtime import wfr


@wfr.activity()  # pyright: ignore[reportCallIssue]
@inject
@span
def notify_summary_available(
    _: WorkflowActivityContext,
    input: NotifySummaryAvailableActivityInput,
    notifier: DaprNotificationService = Provide[Container.notification_service]
) -> bool:
    """
    Send a notification that a summary is available.
    """
    logging.info("Sending summary available notification...")

    campaign_id = input["campaign_id"]
    episode_id = input["episode_id"]
    episode_summary = input["episode_summary"]

    async def run():
        if notifier:
            episode_summary_obj = EpisodeSummary(**episode_summary)
            await notifier.summary_available(SummaryAvailable(
                campaign_id=campaign_id,
                episode_id=episode_id,
                summary=episode_summary_obj.human_summary,
                episode_key=f"campaigns/{campaign_id}/episodes/{episode_id}/summary.json",
                campaign_key=f"campaigns/{campaign_id}/summary.json"
            ))
            logging.info("✅ Summary available notification sent successfully")
            return True
        else:
            logging.info(
                "Notification service not configured, skipping notification.")
            return False

    return asyncio.run(run())
