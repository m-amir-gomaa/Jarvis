import time
import math
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SearchResult:
    chunk_id: str
    source_path: str
    chunk_type: str
    content: str
    start_line: int
    end_line: int
    vector_score: float
    bm25_score: float
    hybrid_score: float
    extra_meta: dict = field(default_factory=dict)

@dataclass
class SearchResultSet:
    results: List[SearchResult]
    latency_ms: float
    query: str

class BM25Scorer:
    """Simple dependency-free BM25 implementation for re-ranking."""
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = []
        self.doc_freqs = []
        self.idf = {}
        
        # Tokenize corpus
        for doc in corpus:
            tokens = self.tokenize(doc)
            self.doc_lengths.append(len(tokens))
            freq = {}
            for t in tokens:
                freq[t] = freq.get(t, 0) + 1
            self.doc_freqs.append(freq)
            
        self.avgdl = sum(self.doc_lengths) / max(1, self.corpus_size)
        
        # Compute IDF
        doc_count_per_term = {}
        for freq in self.doc_freqs:
            for t in freq.keys():
                doc_count_per_term[t] = doc_count_per_term.get(t, 0) + 1
                
        for t, df in doc_count_per_term.items():
            # Standard BM25 IDF formulation
            idf = math.log(1 + (self.corpus_size - df + 0.5) / (df + 0.5))
            self.idf[t] = idf

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\w+', text)]

    def score(self, query: str, doc_index: int) -> float:
        query_tokens = self.tokenize(query)
        score = 0.0
        doc_len = self.doc_lengths[doc_index]
        freqs = self.doc_freqs[doc_index]
        
        for q in query_tokens:
            if q not in freqs:
                continue
            f = freqs[q]
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += self.idf.get(q, 0) * (numerator / denominator)
        return score

class SemanticSearch:
    """
    Combines FAISS vector similarity and BM25 metadata scoring.
    """
    def __init__(self, embedding_engine, faiss_manager):
        self.embedding_engine = embedding_engine
        self.faiss_manager = faiss_manager

    async def search(self, 
                     query: str, 
                     top_k: int = 5, 
                     alpha: float = 0.5, 
                     filters: Optional[Dict[str, str]] = None) -> SearchResultSet:
        """
        Hybrid search using Reciprocal Rank Fusion or Alpha blending.
        alpha=1.0 means only vector search, alpha=0.0 means only BM25.
        Actually, we uses simple min-max normalized weighted sum of scores.
        """
        start_time = time.perf_counter()
        
        # 1. Get query embedding
        query_vector = await self.embedding_engine.embed_text(query, use_cache=True)
        if not query_vector:
            return SearchResultSet([], 0.0, query)
            
        # 2. Fetch broadly from FAISS (e.g., fetch top 50 to rerank and filter)
        fetch_k = max(50, top_k * 3)
        faiss_results = await self.faiss_manager.search(query_vector, top_k=fetch_k)
        if not faiss_results:
            return SearchResultSet([], (time.perf_counter() - start_time) * 1000, query)
            
        # 3. Apply Metadata Filters (source_path, chunk_type)
        if filters:
            filtered_results = []
            for r in faiss_results:
                match = True
                for k, v in filters.items():
                    if r.get(k) != v:
                        match = False
                        break
                if match:
                    filtered_results.append(r)
            faiss_results = filtered_results

        if not faiss_results:
            return SearchResultSet([], (time.perf_counter() - start_time) * 1000, query)

        # 4. Generate BM25 Scores for the subset
        corpus = [r["content"] for r in faiss_results]
        bm25 = BM25Scorer(corpus)
        
        hybrid_results = []
        vec_scores = [r["score"] for r in faiss_results]
        max_vec = max(vec_scores) if vec_scores else 1.0
        min_vec = min(vec_scores) if vec_scores else 0.0
        
        for idx, r in enumerate(faiss_results):
            raw_bm_score = bm25.score(query, idx)
            # Normalize vector score conservatively to 0-1
            norm_vec = r["score"] if max_vec == 0 else (r["score"] - min_vec) / (max_vec - min_vec + 1e-6)
            
            r["bm25_score"] = raw_bm_score
            hybrid_results.append(r)
            
        # Normalize BM25
        bm_scores = [r["bm25_score"] for r in hybrid_results]
        max_bm = max(bm_scores) if bm_scores else 1.0
        min_bm = min(bm_scores) if bm_scores else 0.0
        
        final_results = []
        for r in hybrid_results:
            norm_vec = r["score"] if max_vec == 0 else (r["score"] - min_vec) / (max_vec - min_vec + 1e-6)
            norm_bm = r["bm25_score"] if max_bm == 0 else (r["bm25_score"] - min_bm) / (max_bm - min_bm + 1e-6)
            
            h_score = (alpha * norm_vec) + ((1 - alpha) * norm_bm)
            
            final_results.append(SearchResult(
                chunk_id=r["chunk_id"],
                source_path=r["source_path"],
                chunk_type=r["chunk_type"],
                content=r["content"],
                start_line=r["start_line"],
                end_line=r["end_line"],
                vector_score=r["score"],
                bm25_score=r["bm25_score"],
                hybrid_score=h_score,
                extra_meta=r["extra_meta"]
            ))

        # 5. Sort by hybrid score and return top K
        final_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        top_results = final_results[:top_k]
        
        latency = (time.perf_counter() - start_time) * 1000
        return SearchResultSet(results=top_results, latency_ms=latency, query=query)
