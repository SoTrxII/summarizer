from typing import TypedDict


class Sentence(TypedDict):
    """
    A transcribed sentence from the audio.
    """
    # The start time of the sentence in seconds
    start: float
    # The end time of the sentence in seconds
    end: float
    # The identified speaker (SPEAKER 1, SPEAKER 2, ...)
    speaker: str
    # The transcribed text
    text: str
