import logging
from pathlib import Path

import pytest
from dapr.ext.workflow import DaprWorkflowClient

from summarizer.main import setup_DI
from summarizer.models.sentence import Sentence
from summarizer.workflows.summarize_new_episode import transcript_to_summary

from .utils.json import read_test_data


@pytest.mark.asyncio
async def test_workflow_transcript_to_summary(wf_client: DaprWorkflowClient, data_dir: Path):
    """Test the audio to summary workflow with Dapr sidecar."""
    setup_DI()
    sentences = read_test_data(
        data_dir / "transcriptions" / "10m_diarized.json", Sentence)
    # sentences = read_test_data(
    #     data_dir / "past_campaigns" / "20" / "02.json", Sentence)
    id = wf_client.schedule_new_workflow(
        transcript_to_summary, input=sentences)

    try:
        state = wf_client.wait_for_workflow_completion(
            id, timeout_in_seconds=24*60*60)
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

    except TimeoutError:
        logging.error('*** Workflow timed out!')
        raise
    except Exception as e:
        logging.error(f"Test failed with exception: {e}")
        raise
