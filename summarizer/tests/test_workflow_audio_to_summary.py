import logging

import pytest
from dapr.ext.workflow import DaprWorkflowClient

from summarizer.main import run_workflow_server, setup_DI
from summarizer.workflows.audio_to_summary import audio_to_summary


@pytest.mark.asyncio
async def test_workflow_audio_to_summary(wf_client: DaprWorkflowClient):
    """Test the audio to summary workflow with Dapr sidecar."""
    setup_DI()
    run_workflow_server()
    audio_payload = "1m.ogg"

    id = wf_client.schedule_new_workflow(audio_to_summary, input=audio_payload)

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


@pytest.mark.asyncio
async def test_workflow_audio_to_summary2(wf_client: DaprWorkflowClient):
    """Test the audio to summary workflow with Dapr sidecar."""

    setup_DI()
    run_workflow_server()

    audio_payload = "1m.ogg"
    audio_to_summary(audio_payload)

    id = wf_client.schedule_new_workflow(audio_to_summary, input=audio_payload)

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
