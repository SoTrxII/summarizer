import logging
import os

import pytest
from dapr.ext.workflow import DaprWorkflowClient

from summarizer.main import setup_DI
from summarizer.models.workflow import AudioWorkflowInput
from summarizer.workflows.summarize_new_episode import audio_to_summary
from tests.utils.dapr import managed_workflow_context


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("SKIP_WORKFLOW_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_WORKFLOW_TESTS=true)"
)
async def test_workflow_audio_to_summary(wf_client: DaprWorkflowClient):
    """Test the audio to summary workflow with Dapr sidecar."""
    setup_DI()

    input = AudioWorkflowInput(
        campaign_id=1,
        episode_id=1,
        audio_file_path="1m.ogg"
    )

    # Use context manager to ensure cleanup even if test is interrupted
    with managed_workflow_context(wf_client, audio_to_summary, input) as workflow_id:
        state = wf_client.wait_for_workflow_completion(
            workflow_id, timeout_in_seconds=24*60*60)

        if not state:
            logging.warning("Workflow not found!")
        elif state.runtime_status.name == 'COMPLETED':
            logging.info(
                f'Workflow completed! Result: {state.serialized_output}')
        else:
            # not expected
            logging.error(
                f'Workflow failed! Status: {state.runtime_status.name}')

        # Assert that the workflow completed successfully
        assert state is not None, "Workflow state should not be None"
        assert state.runtime_status.name == 'COMPLETED', f"Workflow should complete successfully, but got status: {state.runtime_status.name}"
