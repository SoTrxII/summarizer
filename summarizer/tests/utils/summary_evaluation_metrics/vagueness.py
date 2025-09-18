import json
from typing import List, Union

import pandas as pd
import spacy
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from pydantic import BaseModel
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
from semantic_kernel.connectors.ai.ollama.ollama_prompt_execution_settings import (
    OllamaChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory

prompt_template = """You are given a list of sentences from a summary of a text.
For each sentence, your job is to evaluate if the sentence is vague, and hence does not help in summarizing the key points of the text.

Vague sentences are those that do not directly mention a main point, e.g. 'this summary describes the reasons for China's AI policy'. 
Such a sentence does not mention the specific reasons, and is vague and uninformative.
Sentences that use phrases such as 'the article suggests', 'the author describes', 'the text discusses' are also considered vague and verbose.

Examples of vague sentences:
1. The text discusses the recent war between Russia and Ukraine, as well as the weapons used.
2. The author analyzes the implications of US semiconductor export controls on China.


Examples of non-vague sentences:
1. China's AI policy revolves around strategic opacity, due to its informational asymmetry with the US.

For each sentence, return a JSON object with the fields:
- `sentence_id`: the `sentence_id` of the sentence
- `is_vague`: a boolean indicating if the sentence is vague
- `reason`: if `is_vague` is true, a concise 1 sentence explanation for why the sentence is vague. If false, give a NIL reply.

Hence return a list of JSON objects. 

SENTENCES:
{sentences}

OUTPUT:"""


class SentenceVagueness(BaseModel):
    sentence_id: int
    is_vague: bool
    reason: str


class SentencesVagueness(BaseModel):
    sentences: List[SentenceVagueness]


class VaguenessMetric(BaseMetric):
    def __init__(self, chat_completion_client: Union[AzureChatCompletion, OllamaChatCompletion], threshold: float = 0.5, nlp_model="en_core_web_sm", verbose_mode: bool = True):
        self.chat_completion_client = chat_completion_client
        self.threshold = threshold
        self.nlp_model = nlp_model
        self.verbose_mode = verbose_mode

    async def _get_text_response(self, prompt: str, settings) -> str:
        """Get text response from either Azure or Ollama provider."""
        if isinstance(self.chat_completion_client, AzureChatCompletion):
            # Azure has get_text_content method
            response = await self.chat_completion_client.get_text_content(prompt, settings=settings)
            return response.text if response else ""
        else:
            # Ollama uses get_chat_message_content with ChatHistory
            chat_history = ChatHistory()
            chat_history.add_user_message(prompt)
            response = await self.chat_completion_client.get_chat_message_content(chat_history, settings=settings)
            return response.content if response else ""

    async def compute_sentences_vagueness(self, sentences: List[str]):
        # Prepare sentences for LLM evaluation
        formatted_sentences = [
            {'sentence_id': i, 'sentence': sentence} for i, sentence in enumerate(sentences)
        ]

        # Format the prompt
        formatted_prompt = prompt_template.format(
            sentences=formatted_sentences)

        # Create execution settings based on the provider type
        if isinstance(self.chat_completion_client, OllamaChatCompletion):
            # Ollama provider - no temperature parameter available
            settings = OllamaChatPromptExecutionSettings()
            settings.format = SentencesVagueness.model_json_schema()
        else:
            # Azure provider
            settings = AzureChatPromptExecutionSettings(temperature=0)
            settings.response_format = SentencesVagueness

        # Get structured response from LLM
        response_text = await self._get_text_response(formatted_prompt, settings)

        # Parse the response
        vagueness_result = SentencesVagueness.model_validate_json(
            response_text)
        vagueness_out = [sentence.model_dump()
                         for sentence in vagueness_result.sentences]

        # Merge with original sentences
        sentences_df = pd.DataFrame(formatted_sentences)
        df = pd.DataFrame(vagueness_out)
        df = df.merge(sentences_df, on='sentence_id')
        return df

    def measure(self, test_case: LLMTestCase):
        # Break the text up into sentences
        assert test_case.actual_output is not None, "Actual output is required for Vagueness Metric"

        # This is a sync method but we need async for the LLM call
        # We'll need to handle this differently - for now, raising an error
        raise NotImplementedError(
            "Use a_measure instead - this metric requires async LLM calls")

    async def a_measure(self, test_case: LLMTestCase):
        # Break the text up into sentences
        assert test_case.actual_output is not None, "Actual output is required for Vagueness Metric"
        sentences = self.split_sentences(test_case.actual_output)
        df = await self.compute_sentences_vagueness(sentences)

        # Score is 1 - % of vague sentences
        self.score = 1 - df['is_vague'].mean()
        self.success = self.score >= self.threshold

        self.verbose_logs = json.dumps(df.to_dict(orient='records'))
        return self.score

    def split_sentences(self, text: str) -> List[str]:
        nlp = spacy.load(self.nlp_model)
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def is_successful(self):
        assert self.success is not None
        return self.success

    @property
    def __name__(self):  # type: ignore
        return "Vagueness Score"
