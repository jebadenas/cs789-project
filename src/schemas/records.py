from dataclasses import dataclass
from typing import Optional

@dataclass
class NumericRecord:
    team: str
    name: str
    email: str
    claimed_contribution: Optional[float]
    perceived_contribution: Optional[float]
    ratings_received: list[Optional[float]]

@dataclass
class TextRecord:
    team: str
    giver_name: str
    giver_email: str
    recipient_team: str
    recipient_name: str
    recipient_email: str
    feedback: str
    givers_comment: str