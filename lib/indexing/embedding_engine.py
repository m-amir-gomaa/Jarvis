import os
import logging
import asyncio
import hashlib
from typing import List, Optional, Union
import numpy as np
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """
    Local-first embedding engine for Jarvis RAG.
    Primary: Ollama (nomic-embed-text)
    Secondary fallback: sentence-transformers
    """
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 primary_model: str = "nomic-embed-text",
                 fallback_model: str = "all-MiniLM-L6-v2",
                 cache_dir: str = "~/.jarvis/index/cache"):
        self.ollama_url = os.environ.get("OLLAMA_BASE_URL", ollama_url)
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._fallback_st = None
        
    def _get_cache_path(self, text: str) -> Path:
        """Generate a deterministic file path for cached embeddings."""
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{h}.npy"

    async def _get_ollama_embedding(self, text: str) -> Optional[List[float]]:
        url = f"{self.ollama_url}/api/embeddings"
        payload = {"model": self.primary_model, "prompt": text}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("embedding")
        except Exception as e:
            logger.debug(f"Ollama embedding failed: {e}")
            return None

    def _get_fallback_embedding(self, text: str) -> List[float]:
        if self._fallback_st is None:
            # Lazy load to avoid import overhead if Ollama is working
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading fallback SentenceTransformer: {self.fallback_model}")
            self._fallback_st = SentenceTransformer(self.fallback_model)
        
        embed = self._fallback_st.encode(text)
        return embed.tolist()
        
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Embed a single text string."""
        cache_path = self._get_cache_path(text)
        if use_cache and cache_path.exists():
            try:
                return np.load(cache_path).tolist()
            except Exception as e:
                logger.warning(f"Failed to load cache from {cache_path}: {e}")
                
        # Primary: Ollama
        embedding = await self._get_ollama_embedding(text)
        
        # Secondary: Sentence Transformers Fallback
        if embedding is None:
            embedding = await asyncio.to_thread(self._get_fallback_embedding, text)
            
        if use_cache and embedding:
            np.save(cache_path, np.array(embedding, dtype=np.float32))
            
        return embedding

    async def embed_batch(self, texts: List[str], use_cache: bool = True) -> np.ndarray:
        """Embed a batch of texts concurrently."""
        tasks = [self.embed_text(text, use_cache=use_cache) for text in texts]
        embeddings = await asyncio.gather(*tasks)
        return np.array(embeddings, dtype=np.float32)

def cosine_similarity(vec1: Union[List[float], np.ndarray], vec2: Union[List[float], np.ndarray]) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))
