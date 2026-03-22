from dataclasses import dataclass, field
from .question import Question

@dataclass
class Session:
    course: str
    name: str
    year: str
    number: int
    semester: str
    questions: dict[int, Question] = field(default_factory=dict)