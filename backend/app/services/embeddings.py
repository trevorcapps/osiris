import logging
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model = None

    def load(self):
        try:
            self.model = SentenceTransformer(settings.embedding_model)
            logger.info(f"Loaded embedding model: {settings.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")

    def embed(self, text: str) -> List[float]:
        if not self.model:
            return [0.0] * 384
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.model:
            return [[0.0] * 384 for _ in texts]
        return [e.tolist() for e in self.model.encode(texts, batch_size=32)]


embedding_service = EmbeddingService()
