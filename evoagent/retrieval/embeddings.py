"""BaseEmbeddingModel and MockEmbeddingModel for text embeddings."""

import hashlib
from abc import ABC, abstractmethod


class BaseEmbeddingModel(ABC):
    """Abstract embedding model for generating text vectors."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        return [self.embed_text(t) for t in texts]


class MockEmbeddingModel(BaseEmbeddingModel):
    """Deterministic mock embedding using SHA256 hash → 64-dim vectors.

    No network calls, always returns the same vector for the same text.
    """

    DIM = 64

    def embed_text(self, text: str) -> list[float]:
        vec: list[float] = []
        block = 0
        # A single SHA-256 digest yields only 8 four-byte values; hash
        # additional salted blocks until every dimension has real signal
        # (instead of zero-padding 56 of 64 dims).
        while len(vec) < self.DIM:
            h = hashlib.sha256(f"{block}:{text}".encode()).digest()
            for i in range(0, len(h), 4):
                if len(vec) >= self.DIM:
                    break
                val = int.from_bytes(h[i:i + 4], "big") / (2**32)
                vec.append(val * 2 - 1)
            block += 1
        return vec
