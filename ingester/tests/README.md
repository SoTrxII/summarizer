# Dapr Testing with Pytest

This directory contains pytest fixtures and tests for working with Dapr workflows.

## Fixtures Available

### `dapr_sidecar` (session-scoped)

This fixture automatically starts a Dapr sidecar before running your tests and cleans it up afterward.
**Important: Only runs when tests are marked with `@pytest.mark.e2e`**

**What it does:**
- Checks if any test in the session has the 'e2e' marker
- Starts a Dapr sidecar process with the correct configuration (only for e2e tests)
- Waits for the sidecar to become healthy
- Provides sidecar information (ports, app_id, etc.)
- Automatically cleans up the sidecar when tests complete

**Usage:**
```python
@pytest.mark.e2e
def test_something_with_dapr(dapr_sidecar):
    sidecar_info = dapr_sidecar
    # sidecar_info contains: app_id, http_port, grpc_port, process
    
    # Your test code here - Dapr is running and ready
```

### `dapr_client`

This fixture provides a pre-configured `DaprWorkflowClient` that's ready to use.
**Note: Will skip tests that don't have the `e2e` marker.**

**Usage:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_workflow(dapr_client):
    wf_client = dapr_client
    
    # Schedule a workflow
    instance_id = wf_client.schedule_new_workflow(my_workflow, input=data)
    
    # Wait for completion
    state = wf_client.wait_for_workflow_completion(instance_id, timeout_in_seconds=30)
```

### `setup_logging` (auto-use)

This fixture automatically configures logging for all tests.

## Test Markers

- `@pytest.mark.e2e`: End-to-end tests that require Dapr sidecar
- `@pytest.mark.unit`: Unit tests (no external dependencies)  
- `@pytest.mark.integration`: Integration tests

**Important**: The Dapr sidecar will only start if there are tests marked with `e2e` in the test session.

## Example Usage

See `test_dapr_fixture_example.py` for examples of how to use these fixtures.

## Configuration

The Dapr sidecar is configured with:
- App ID: `summarizer`
- HTTP Port: `3500`
- gRPC Port: `50001`
- Components Path: `../components` (relative to workspace root)

## Requirements

Make sure you have:
1. Dapr CLI installed
2. `requests` library installed (for health checks)
3. `pytest` and `pytest-asyncio` installed

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (no Dapr sidecar will start)
pytest -m "not e2e"

# Run only e2e tests (Dapr sidecar will start)
pytest -m e2e

# Run a specific test file
pytest tests/test_dapr_fixture_example.py

# Run with verbose output
pytest -v

# Run with logging output
pytest -s
```

## Notes

- The `dapr_sidecar` fixture is session-scoped, meaning it starts once per test session and is shared across all tests
- The sidecar runs with a dummy app (`sleep infinity`) - it's just providing the Dapr runtime, not running your actual application
- Health checks ensure the sidecar is ready before tests run
- Automatic cleanup ensures no lingering processes after tests complete
