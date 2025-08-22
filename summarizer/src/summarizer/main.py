import asyncio
import logging
from typing import Never

from dapr.ext.workflow import DaprWorkflowClient
from dotenv import load_dotenv

from summarizer.container import Container
from summarizer.workflows.audio_to_summary import audio_to_summary
from summarizer.workflows.runtime import wfr

load_dotenv()


def setup_DI() -> None:
    """
    Create and inject dependencies into the dependency injection container.
    This will fail if any required environment variables are missing.
    """
    container = Container()

    (
        container
        .config
        .hugging_face_token
        .from_env("HUGGING_FACE_TOKEN", required=True)
    )
    (
        container
        .config
        .foundry_endpoint
        .from_env("AI_FOUNDRY_PROJECT_ENDPOINT", required=True)
    )
    (
        container
        .config
        .chat_deployment_name
        .from_env("CHAT_DEPLOYMENT_NAME", required=True)
    )
    container.wire(modules=[audio_to_summary])


def start_workflow_server() -> None:
    """
    Start the remote workflow runtime
    """
    wfr.start()


async def main() -> Never:
    """
    Runs the workflow server and waits indefinitely.
    """
    setup_DI()
    start_workflow_server()
    await asyncio.Event().wait()
    raise RuntimeError("Unreachable")


async def main2() -> None:
    """
    Runs the workflow server and waits indefinitely.
    """
    setup_DI()
    start_workflow_server()
    wf_client = DaprWorkflowClient()
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

if __name__ == "__main__":
    asyncio.run(main2())
