"""
This module only export the Dapr Workflow Runtime as a singleton
"""
from dapr.ext.workflow import WorkflowRuntime

wfr = WorkflowRuntime()
