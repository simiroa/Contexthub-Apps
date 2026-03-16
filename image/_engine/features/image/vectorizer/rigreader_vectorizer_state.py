from __future__ import annotations

from dataclasses import dataclass

from features.image.vectorizer.state import VectorizerState


@dataclass
class RigreaderVectorizerState(VectorizerState):
    status_level: str = "ready"
