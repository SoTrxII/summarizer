import logging
import os
from pathlib import Path
from shutil import copyfile

import pytest
from dapr.ext.workflow import DaprWorkflowClient

from summarizer.main import setup_DI
from summarizer.models.workflow import WorkflowInput
from summarizer.workflows.summarize_new_episode import transcript_to_summary
from tests.utils.dapr import managed_workflow_context


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("SKIP_WORKFLOW_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_WORKFLOW_TESTS=true)"
)
async def test_workflow_transcript_to_summary(wf_client: DaprWorkflowClient, data_dir: Path):
    """Test the transcript to summary workflow with Dapr sidecar."""
    setup_DI()
    asset_name = "1m_sample1.json"
    # asset_name = "02.json"

    # Ensure the target directory exists before copying the file
    target_dir = data_dir / "generated" / "1" / "2"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy the target test file to the generated directory, which is where the test summary-store
    # points to
    copyfile(
        data_dir / "transcriptions" / asset_name,
        target_dir / "transcript.json"
    )
    # copyfile(
    #     data_dir / "past_campaigns" / "14" / asset_name,
    #     target_dir / "transcript.json"
    # )

    # Create workflow input
    input = WorkflowInput(
        campaign_id=1,
        episode_id=2
    )

    # Use context manager to ensure cleanup even if test is interrupted
    with managed_workflow_context(wf_client, transcript_to_summary, input) as workflow_id:
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
