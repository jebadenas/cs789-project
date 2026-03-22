from dataclasses import dataclass, field
from typing import Union
from .records import NumericRecord, TextRecord

@dataclass
class Question:
    number: int
    text: str
    question_type: str                # "numeric" or "text"
    records: list[Union[NumericRecord, TextRecord]] = field(default_factory=list)