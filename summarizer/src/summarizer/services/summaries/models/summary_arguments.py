
from dataclasses import dataclass
from typing import Optional


@dataclass
class SummaryArguments:
    """ Language of the produced summary """
    language: Optional[str] = "English"
