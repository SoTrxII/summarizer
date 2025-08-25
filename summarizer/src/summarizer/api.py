"""
HTTP API server for starting and monitoring workflows.
"""
import logging

from dapr.ext.workflow import DaprWorkflowClient
from fastapi import FastAPI, HTTPException
from pydantic import TypeAdapter, ValidationError

from summarizer.models.workflow import (
    AudioWorkflowInput,
    WorkflowInput,
    WorkflowStartResponse,
)
from summarizer.workflows.summarize_new_episode import (
    audio_to_summary,
    transcript_to_summary,
)

# FastAPI app
app = FastAPI(
    title="Summarizer Workflow API",
    description="HTTP API for starting and monitoring audio summarization workflows",
    version="1.0.0"
)

wf_client = DaprWorkflowClient()


@app.post("/workflows/audio", response_model=WorkflowStartResponse)
async def start_audio_workflow(input: AudioWorkflowInput):
    """Start an audio-to-summary workflow."""
    ta = TypeAdapter(AudioWorkflowInput)
    try:
        ta.validate_python(input)
        w_id = wf_client.schedule_new_workflow(audio_to_summary, input=input)
        logging.info(f"Started audio-to-summary workflow with ID: {w_id}")
        return WorkflowStartResponse(
            workflow_id=w_id,
            message=f"Started audio-to-summary workflow for campaign {input['campaign_id']}, episode {input['episode_id']}"
        )
    except ValidationError as e:
        logging.warning(f"Rejected request: {e}")
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/workflows/transcript", response_model=WorkflowStartResponse)
async def start_transcript_workflow(input: WorkflowInput):
    """Start a transcript-to-summary workflow."""
    ta = TypeAdapter(WorkflowInput)
    try:
        ta.validate_python(input)
        w_id = wf_client.schedule_new_workflow(
            transcript_to_summary, input=input)
        logging.info(f"Started transcript-to-summary workflow with ID: {w_id}")
        return WorkflowStartResponse(
            workflow_id=w_id,
            message=f"Started transcript-to-summary workflow for campaign {input['campaign_id']}, episode {input['episode_id']}"
        )
    except ValidationError as e:
        logging.warning(f"Rejected request: {e}")
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get the status of a specific workflow."""
    return wf_client.get_workflow_state(workflow_id)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Summarizer Workflow API is running"}
