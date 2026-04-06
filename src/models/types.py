"""Shared result types for IWF models."""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict

from src.parsing.schemas import StudentInfo


class ModelResult(BaseModel):
    """Result returned by every IWF model.

    Required fields are populated by all models.  Optional fields are
    used only by iterative models (PeerRank, PeerHITS).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str
    iwf_vector: np.ndarray
    students: list[StudentInfo]

    # Iterative-model convergence metadata
    iterations: Optional[int] = None
    converged: Optional[bool] = None
    final_l1_norm: Optional[float] = None

    # PeerHITS dual-score vector
    hub_vector: Optional[np.ndarray] = None
