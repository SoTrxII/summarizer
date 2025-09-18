from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCaseParams


def repetitiveness_factory(model: str | DeepEvalBaseLLM) -> GEval:
    """
    Factory function to create a repetitiveness metric instance.
    """
    return GEval(
        name="Repetitiveness",
        criteria="""Evaluate if the summary contains unnecessary repetitive information.
        
        SCORING:
        - Score 1.0: Summary has NO unnecessary repetition - each fact or main point is mentioned only once
        - Score 0.0: Summary has significant unnecessary repetition - facts or main points are repeated unnecessarily
        
        GUIDELINES:
        - Points on the same topic discussing different aspects are acceptable and not considered repetition
        - Only count as repetition when the same fact or main point is restated without adding new information
        - In your reasoning, explicitly state whether repetition was found and point out any unnecessarily repetitive points
        
        Return a score of exactly 1.0 if no unnecessary repetition is found, or 0.0 if unnecessary repetition exists.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        verbose_mode=True,
        model=model,
    )
