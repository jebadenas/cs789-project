"""Pydantic schemas for peer-assessment score matrices."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator


class StudentInfo(BaseModel):
    """A student's identity and position within a ScoreMatrix."""

    name: str
    email: str
    index: int


class ScoreMatrix(BaseModel):
    """N×N peer-assessment score matrix with metadata.

    matrix[i][j] = score that giver j assigned to recipient i.
    Rows are recipients, columns are givers.
    Students are ordered alphabetically by email.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    matrix: np.ndarray
    team_name: str
    question_label: str
    year: str
    semester: str
    session_number: int
    students: list[StudentInfo]
    excluded_students: list[StudentInfo] = []

    @model_validator(mode="after")
    def _validate_shape(self) -> ScoreMatrix:
        n = len(self.students)
        if self.matrix.shape != (n, n):
            raise ValueError(
                f"Matrix shape {self.matrix.shape} doesn't match {n} students"
            )
        return self

    @property
    def name_to_index(self) -> dict[str, int]:
        return {s.name: s.index for s in self.students}

    @property
    def email_to_index(self) -> dict[str, int]:
        return {s.email: s.index for s in self.students}
