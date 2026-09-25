"""Shared invariants and provider-neutral value types."""
from dataclasses import dataclass, asdict
from typing import Protocol
import hashlib
import json
import re

CONFIG = dict(version="1", manuscript_access=False, external_connectors=False,
              remote_model_calls=False, engine="deterministic-v1")

class BoundaryError(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def fingerprint(data):
    return hashlib.sha256(data).hexdigest()

def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise BoundaryError("Use an anonymous identifier of 1-64 letters, digits, _ or -.")
    return value

@dataclass(frozen=True)
class EvidenceSpan:
    review_id: str
    quote: str
    start: int
    end: int
    paragraph: int
    source_hash: str
    normalization_version: int

    def validate(self, review):
        text = review["text"]
        if (self.review_id != review["review_id"] or self.source_hash != review["source_hash"]
            or self.normalization_version != review["version"]
            or not 0 <= self.start < self.end <= len(text)
            or text[self.start:self.end] != self.quote
            or self.paragraph != text[:self.start].count("\n") + 1):
            raise BoundaryError("Evidence does not resolve to the versioned normalized review.")
        return asdict(self)

class AnalysisEngine(Protocol):
    version: str
    def propose(self, reviews: list[dict]) -> dict: ...
