import datetime
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.ollama.ollama_prompt_execution_settings import (
    OllamaChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig
from yaml import safe_load


def load_prompt(path: Path) -> PromptTemplateConfig:
    """
    Load a prompt template from a yaml file
    :param path: Path to the yaml file
    :return: The prompt template configuration
    """
    with open(path, "r") as file:
        template_definition = file.read()

    data = safe_load(template_definition)
    return PromptTemplateConfig(**data)


def load_agent(path: Path, kernel: Kernel, format: Optional[Type[BaseModel]] = None) -> ChatCompletionAgent:
    """
    Load an agent from a yaml file
    :param path: Path to the yaml file
    :param kernel: The kernel to use for the agent
    :param format: Optional response format for the agent
    :return: The agent
    """

    agent_definition = load_prompt(path)
    # settings = kernel.get_prompt_execution_settings_from_service_id()

    # Configure the function choice behavior to auto invoke kernel functions
    id = kernel.get_service(type=ChatCompletionClientBase).ai_model_id
    settings = kernel.get_prompt_execution_settings_from_service_id(id)
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # Note : The manner to set the structured output is not yet unified
    # So i'll let it hardcoded for the time being
    # TODO : Remove this when the structured output is unified
    match settings:
        case OllamaChatPromptExecutionSettings():
            settings.format = format.model_json_schema()  # type: ignore
        case AzureChatPromptExecutionSettings():
            settings.response_format = format  # type: ignore
        case _:
            raise ValueError(f"Unknown prompt execution settings: {settings}")

    # settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
    # Note : Without a kernel ref, the agent creation will create a new kernel
    return ChatCompletionAgent(
        kernel=kernel,
        name=agent_definition.name,
        description=agent_definition.description,
        prompt_template_config=agent_definition,
        arguments=KernelArguments(
            now=datetime.datetime.now().isoformat(),
            # TODO: Make into a variable
            language="French",
            settings=settings,
        )
    )
