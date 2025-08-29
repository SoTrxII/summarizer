"""
Utilities to manage Dapr lifecyle in testing
"""
import logging
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import requests
from dapr.ext.workflow import DaprWorkflowClient

from summarizer.workflows.runtime import wfr


def _wait_for_dapr_sidecar(port, max_attempts=10, delay=1):
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"http://localhost:{port}/v1.0/healthz", timeout=2)
            if response.status_code == 204:
                logging.info(
                    f"Dapr sidecar is ready after {attempt + 1} attempts")
                return True
            else:
                logging.warning(
                    f"Health check failed: {response.status_code} - {response.text}")
        except (requests.RequestException, ConnectionError):
            pass
        logging.info(
            f"Dapr not ready (attempt {attempt + 1}/{max_attempts}), retrying...")
        time.sleep(delay)
    return False


def wait_for_workflow_purge(client: DaprWorkflowClient, workflow_id: str, timeout_seconds: int = 30) -> None:
    """
    Wait for a workflow to be purged by polling its state until it's no longer found.

    Args:
        client: The Dapr workflow client
        workflow_id: The ID of the workflow to wait for purge
        timeout_seconds: Maximum time to wait for purge completion

    Raises:
        TimeoutError: If the workflow is not purged within the timeout period
    """
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            state = client.get_workflow_state(workflow_id)
            if state is None:
                # Workflow has been purged (no longer exists)
                logging.info(
                    f"Workflow {workflow_id} has been successfully purged")
                return
            else:
                # Workflow still exists, wait a bit and check again
                time.sleep(0.5)
        except Exception as e:
            # If we get an exception (like "workflow not found"), consider it purged
            logging.info(
                f"Workflow {workflow_id} appears to be purged (exception: {e})")
            return

    raise TimeoutError(
        f"Workflow {workflow_id} was not purged within {timeout_seconds} seconds")


@contextmanager
def managed_workflow_context(wf_client: DaprWorkflowClient, workflow_func, input_data):
    """
    Context manager that ensures workflow cleanup even if interrupted.
    """
    workflow_id = None
    try:
        workflow_id = wf_client.schedule_new_workflow(
            workflow_func, input=input_data)
        logging.info(f"Started workflow {workflow_id}")
        yield workflow_id
    finally:
        if workflow_id:
            logging.info(f"Cleaning up workflow {workflow_id}...")
            try:
                wf_client.terminate_workflow(workflow_id, recursive=True)
                wf_client.purge_workflow(workflow_id, recursive=True)
                wait_for_workflow_purge(
                    wf_client, workflow_id, timeout_seconds=30)
                logging.info("Workflow cleanup completed successfully")
            except Exception as e:
                logging.error(f"Error during workflow cleanup: {e}")


def start_dapr_client() -> Generator[DaprWorkflowClient, None, None]:
    """
    Start a Dapr sidecar and return a workflow client.
    This function handles all the Dapr initialization logic.
    """

    # Workspace and component paths
    workspace_root = Path(__file__).parent.parent.parent.parent
    components_path = workspace_root / "components"

    app_id = "summarizer-testing"
    dapr_http_port = "3500"
    dapr_grpc_port = "50001"

    # Try to find daprd executable in common locations
    daprd_paths = [
        "/home/vscode/.dapr/bin/daprd",  # Dev container
        "/home/runner/.dapr/bin/daprd",  # GitHub Actions
        os.path.expanduser("~/.dapr/bin/daprd"),  # User home
        "daprd"  # System PATH
    ]

    daprd_path = None
    for path in daprd_paths:
        if path == "daprd":
            # Check if daprd is available in PATH
            try:
                subprocess.run(["which", "daprd"], check=True,
                               capture_output=True)
                daprd_path = path
                break
            except subprocess.CalledProcessError:
                continue
        elif os.path.exists(path):
            daprd_path = path
            break

    if not daprd_path:
        error_msg = "Could not find daprd executable. Please ensure Dapr is installed.\n"
        error_msg += "Searched locations:\n"
        for path in daprd_paths:
            exists = "✓" if (path == "daprd" and os.system(
                "which daprd >/dev/null 2>&1") == 0) or os.path.exists(path) else "✗"
            error_msg += f"  {exists} {path}\n"
        error_msg += "To install Dapr, run: curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | /bin/bash"
        raise RuntimeError(error_msg)

    cmd = [
        daprd_path,
        "--app-id", app_id,
        "--dapr-http-port", dapr_http_port,
        "--dapr-grpc-port", dapr_grpc_port,
        "--placement-host-address", "0.0.0.0:50005",
        "--scheduler-host-address", "0.0.0.0:50006",
        "--resources-path", str(components_path.resolve()),
        "--config", str((components_path / "dapr-config.yaml").resolve()),
        "--log-level", "debug",  # Enable debug logs
    ]

    logging.info(f"Starting Dapr sidecar with: {' '.join(cmd)}")

    log_dir = Path(__file__).parent.parent / "logs"
    # Create the logs directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)
    stdout = "dapr_stdout.log"
    stderr = "dapr_stderr.log"

    with open(log_dir / stdout, "w") as stdout_file, open(log_dir / stderr, "w") as stderr_file:
        process = subprocess.Popen(
            cmd,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
            cwd=str(workspace_root)
        )

        if not _wait_for_dapr_sidecar(dapr_http_port):
            process.terminate()
            with open(log_dir / stdout, "r") as stdout_file, open(log_dir / stderr, "r") as stderr_file:
                print("=== Dapr stdout ===")
                print(stdout_file.read())
                print("=== Dapr stderr ===")
                print(stderr_file.read())
            raise RuntimeError("Dapr sidecar failed to start")

        try:
            wfr.start()
            yield DaprWorkflowClient(host="0.0.0.0", port=dapr_grpc_port)
            wfr.shutdown()
        finally:
            # Cleanup Dapr process
            logging.info("Shutting down Dapr sidecar...")
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                logging.warning("Force killing Dapr sidecar process...")
                process.kill()
