import json

import spacy
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from nltk import word_tokenize


class EntityDensityMetric(BaseMetric):
    def __init__(self, optimal_density: float = 0.15, *, nlp_model="en_core_web_sm", threshold: float = 0.95, verbose_mode: bool = True):
        self.nlp = spacy.load(nlp_model)
        self.optimal_density = optimal_density
        self.verbose_mode = verbose_mode
        self.threshold = threshold

    def compute_entity_density(self, text: str):
        summary_tokens = word_tokenize(text)
        num_tokens = len(summary_tokens)

        # Extract entities
        doc = self.nlp(text)
        num_entities = len(doc.ents)
        entity_density = num_entities / num_tokens

        return entity_density, num_entities, num_tokens

    def measure(self, test_case: LLMTestCase):

        assert test_case.actual_output is not None, "Actual output is required for Entity Density Metric"
        # Break the text up into sentences
        entity_density, num_entities, num_tokens = self.compute_entity_density(
            test_case.actual_output)

        # Score is the absolute difference between the entity density and the optimal density
        self.score = 1 - abs(entity_density - self.optimal_density)
        self.success = self.score <= self.threshold

        logs = {
            'entity_density': entity_density,
            'num_entities': num_entities,
            'num_tokens': num_tokens,
        }

        self.verbose_logs = json.dumps(logs)
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self):
        assert self.success is not None
        return self.success

    @property
    def __name__(self):  # type: ignore
        return "Entity Density Score"
