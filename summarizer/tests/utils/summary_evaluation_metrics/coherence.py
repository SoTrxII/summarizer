import json
from typing import List

import numpy as np
import spacy
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer


class CoherenceMetric(BaseMetric):
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", *, nlp_model="en_core_web_sm", threshold: float = 0.4, verbose_mode: bool = True, device='cpu'):
        self.threshold = threshold
        self.embedding_model = embedding_model
        self.nlp_model = nlp_model
        self.verbose_mode = verbose_mode
        self.device = device
        self.sentence_similarities = []

    def compute_coherence_score(self, sentences: List[str]):

        embedding_model = SentenceTransformer(
            self.embedding_model, device=self.device
        )
        sentences_embeddings = embedding_model.encode(sentences)

        for i in range(len(sentences_embeddings) - 2):
            # Convert embeddings to numpy arrays and reshape to 2D
            emb1 = np.array(sentences_embeddings[i])
            emb2 = np.array(sentences_embeddings[i+2])
            # Calculate cosine distance
            distance = cosine(emb1, emb2)
            similarity = 1 - distance
            self.sentence_similarities.append(similarity)
        coherence_score = np.mean(self.sentence_similarities)
        return coherence_score.__float__()

    def measure(self, test_case: LLMTestCase):

        # Break the text up into sentences
        actual_output = test_case.actual_output or ""
        sentences = self.split_sentences(actual_output)
        self.score = self.compute_coherence_score(sentences)
        self.success = self.score >= self.threshold

        logs = {
            'sentences': sentences,
            'sentence_similarities': [float(s) for s in self.sentence_similarities],
        }
        self.verbose_logs = json.dumps(logs)
        return self.score

    async def a_measure(self, test_case: LLMTestCase):
        return self.measure(test_case)

    def is_successful(self):
        if not hasattr(self, 'success') or self.success is None:
            raise ValueError("Must call measure() before checking success.")
        return self.success

    def split_sentences(self, text: str) -> List[str]:
        nlp = spacy.load(self.nlp_model)
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    @property
    def __name__(self):  # type: ignore
        return "Coherence Score"
