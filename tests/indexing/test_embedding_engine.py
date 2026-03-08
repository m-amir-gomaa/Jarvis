import pytest
import numpy as np
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from lib.indexing.embedding_engine import EmbeddingEngine, cosine_similarity

@pytest.fixture
def engine(tmp_path):
    return EmbeddingEngine(cache_dir=str(tmp_path))

@pytest.mark.asyncio
async def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v2), 1.0)
    
    v3 = [0.0, 1.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v3), 0.0)
    
    # Handle zero vectors safely
    v4 = [0.0, 0.0, 0.0]
    assert np.isclose(cosine_similarity(v1, v4), 0.0)

@pytest.mark.asyncio
async def test_embed_text_ollama_success(engine):
    with patch("lib.indexing.embedding_engine.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_post.return_value = mock_response

        embedding = await engine.embed_text("hello ollama", use_cache=False)

        assert np.allclose(embedding, [0.1, 0.2, 0.3])
        mock_post.assert_called_once()
        
@pytest.mark.asyncio
async def test_embed_text_fallback(engine):
    with patch("lib.indexing.embedding_engine.EmbeddingEngine._get_ollama_embedding", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = None
        
        with patch("sentence_transformers.SentenceTransformer") as mock_st_class:
            mock_st_instance = MagicMock()
            mock_st_instance.encode.return_value = np.array([0.4, 0.5, 0.6])
            mock_st_class.return_value = mock_st_instance
            
            embedding = await engine.embed_text("fallback text", use_cache=False)
            assert embedding == [0.4, 0.5, 0.6]

@pytest.mark.asyncio
async def test_caching(engine):
    with patch("lib.indexing.embedding_engine.EmbeddingEngine._get_ollama_embedding", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = [0.1, 0.1, 0.1]
        
        # First call hits mocked ollama and caches it
        res1 = await engine.embed_text("cache me", use_cache=True)
        assert res1 == [0.1, 0.1, 0.1]
        assert mock_ollama.call_count == 1
        
        # Second call hits cache, shouldn't increment ollama call count
        mock_ollama.return_value = [0.9, 0.9, 0.9] # Different value to prove it loaded from cache
        res2 = await engine.embed_text("cache me", use_cache=True)
        
        assert np.allclose(res2, [0.1, 0.1, 0.1])
        assert mock_ollama.call_count == 1
        
@pytest.mark.asyncio
async def test_batching(engine):
    with patch("lib.indexing.embedding_engine.EmbeddingEngine.embed_text", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = [[0.1, 0.2], [0.3, 0.4]]
        
        texts = ["text1", "text2"]
        res = await engine.embed_batch(texts, use_cache=False)
        
        assert isinstance(res, np.ndarray)
        assert res.shape == (2, 2)
        assert np.allclose(res[0], [0.1, 0.2])
        assert np.allclose(res[1], [0.3, 0.4])
