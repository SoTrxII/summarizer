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


@pytest.mark.parametrize("campaign_id,episode_id,asset_name,is_one_shot,test_description", [
    (5, 1, "1m_sample1.json", False, "regular episode"),
    (6, 1, "1m_sample2.json", True, "one-shot episode")
])
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("SKIP_WORKFLOW_TESTS", "false").lower() == "true",
    reason="Workflow tests skipped in CI (SKIP_WORKFLOW_TESTS=true)"
)
async def test_workflow_transcript_to_summary(wf_client: DaprWorkflowClient, data_dir: Path, campaign_id: int, episode_id: int, asset_name: str, is_one_shot: bool, test_description: str):
    """Test the transcript to summary workflow with Dapr sidecar."""
    setup_DI()

    # Ensure the target directory exists before copying the file
    target_dir = data_dir / "generated" / f"{campaign_id}" / f"{episode_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy the target test file to the generated directory, which is where the test summary-store
    # points to
    copyfile(
        data_dir / "transcriptions" / asset_name,
        target_dir / "transcript.json"
    )

    # Create workflow input
    input = WorkflowInput(
        campaign_id=campaign_id,
        episode_id=episode_id,
        is_one_shot=is_one_shot
    )

    # Use context manager to ensure cleanup even if test is interrupted
    with managed_workflow_context(wf_client, transcript_to_summary, input) as workflow_id:
        state = wf_client.wait_for_workflow_completion(
            workflow_id, timeout_in_seconds=24*60*60)

        if not state:
            logging.warning(f"Workflow not found for {test_description}!")
        elif state.runtime_status.name == 'COMPLETED':
            logging.info(
                f'{test_description.capitalize()} workflow completed! Result: {state.serialized_output}')
        else:
            # not expected
            logging.error(
                f'{test_description.capitalize()} workflow failed! Status: {state.runtime_status.name}')

        # Assert that the workflow completed successfully
        assert state is not None, f"{test_description.capitalize()} workflow state should not be None"
        assert state.runtime_status.name == 'COMPLETED', f"{test_description.capitalize()} workflow should complete successfully, but got status: {state.runtime_status.name}"
