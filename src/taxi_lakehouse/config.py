"""Validated runtime configuration, included in the processing identity."""

import hashlib
import json
from dataclasses import asdict, dataclass

MODEL_VERSION = "2"


@dataclass(frozen=True)
class PipelineConfig:
    max_reject_ratio: float = 0.10
    memory_limit: str = "2GB"
    threads: int = 2
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        if not 0 <= self.max_reject_ratio <= 1:
            raise ValueError("max_reject_ratio must be between 0 and 1")
        if self.threads < 1:
            raise ValueError("threads must be positive")
        if not self.model_version:
            raise ValueError("model_version must not be empty")

    @property
    def fingerprint(self) -> str:
        # Resource budgets do not change the business output.
        payload = {"model_version": self.model_version, "max_reject_ratio": self.max_reject_ratio}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def as_dict(self) -> dict:
        return asdict(self)
