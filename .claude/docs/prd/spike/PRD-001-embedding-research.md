---
title: Embedding Model Research for Semantic Search
type: spike
status: complete
created: 2025-12-22
priority: P0
---

# Embedding Model Research for SkillMeat CLI

## Executive Summary

**Recommendation**: Local sentence-transformers with SQLite vector storage.

**Rationale**: Desktop CLI tools prioritize offline capability, zero marginal cost, and instant response. Local embeddings meet all requirements with acceptable memory footprint (~100MB).

---

## Option 1: Local Embedding Models (RECOMMENDED)

### sentence-transformers

**Model**: `all-MiniLM-L6-v2` (most popular lightweight option)

**Specifications**:
- Model size: ~80MB on disk
- Memory usage: ~100MB loaded
- Embedding dimension: 384
- Inference speed: ~1000 sentences/sec on CPU
- Quality: 58.8 on STS benchmark (good for general similarity)

**Integration**:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["artifact description"])
```

**Pros**:
- ✅ Fully offline (no API dependency)
- ✅ Zero marginal cost
- ✅ Fast (<10ms per query on modern CPU)
- ✅ Mature ecosystem (HuggingFace)
- ✅ Easy installation via pip

**Cons**:
- ❌ Initial model download (~80MB)
- ❌ Memory overhead when loaded
- ❌ Requires Python ML dependencies (torch)

**Caching Strategy**:
Store embeddings in SQLite with artifact metadata:
```sql
CREATE TABLE artifact_embeddings (
    artifact_id TEXT PRIMARY KEY,
    embedding BLOB,  -- numpy array serialized
    content_hash TEXT,  -- invalidate on content change
    created_at TIMESTAMP
);
```

Regenerate only when:
- Artifact content changes (detect via hash)
- Model version upgrades
- User forces refresh

**Alternative Models**:
- `paraphrase-MiniLM-L3-v2`: Smaller (61MB), faster, slightly lower quality
- `multi-qa-MiniLM-L6-cos-v1`: Optimized for Q&A matching (better for "how do I..." queries)

---

## Option 2: Haiku 4.5 Sub-Skill Approach

### Feasibility Analysis

**Mechanism**: Invoke Claude via skill to generate text embeddings or similarity scores.

**Challenge**: Claude models don't expose raw embeddings. Would require:
1. Asking Claude to score similarity (0-1) for each query-artifact pair
2. OR: Ask Claude to extract/generate semantic features as JSON

**Example Flow**:
```python
# Hypothetical skill invocation
skill_response = invoke_skill("embedding-generator", {
    "text": "artifact description",
    "format": "feature_vector"
})
```

**Pros**:
- ✅ No local ML dependencies
- ✅ Potentially higher semantic understanding (Claude's reasoning)

**Cons**:
- ❌ Requires API access (not offline)
- ❌ High latency (~500ms+ per embedding vs <10ms local)
- ❌ Cost per query (not suitable for real-time search over 100+ artifacts)
- ❌ No official embedding API from Anthropic
- ❌ Caching required for all artifacts (defeats "zero-shot" benefit)

**Verdict**: Not viable for CLI semantic search. Better suited for one-off similarity tasks.

---

## Option 3: External Embedding APIs

### OpenAI Embeddings

**Model**: `text-embedding-3-small` (latest, cheapest)

**Specifications**:
- Cost: $0.02 / 1M tokens (~$0.00002 per artifact description)
- Dimension: 1536 (configurable down to 512)
- Latency: ~100-300ms per request
- Quality: State-of-the-art (68.0 on MTEB benchmark)

**Pros**:
- ✅ Best quality embeddings
- ✅ No local model management
- ✅ Small dependency (openai Python package)

**Cons**:
- ❌ Requires internet + API key
- ❌ Ongoing cost (small but not zero)
- ❌ Latency unsuitable for real-time CLI UX
- ❌ Privacy concern (artifact metadata sent to OpenAI)

### Cohere Embed

**Model**: `embed-english-light-v3.0`

**Specifications**:
- Cost: $0.10 / 1M tokens
- Dimension: 384
- Similar latency to OpenAI

**Verdict**: More expensive than OpenAI, no significant benefit for CLI use case.

---

## Recommended Implementation

### Phase 1: Local Embeddings with Lazy Loading

**Setup**:
```python
# skillmeat/core/search/embeddings.py
class EmbeddingService:
    def __init__(self, cache_dir: Path):
        self.model = None  # Load lazily
        self.cache = SQLiteCache(cache_dir / "embeddings.db")

    def embed(self, text: str) -> np.ndarray:
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        return self.model.encode(text)
```

**Search Flow**:
1. User query → embed query (10ms)
2. Load cached artifact embeddings from SQLite
3. Compute cosine similarity (numpy vectorized operation)
4. Return top-K matches (sorted by score)

**Caching**:
- Pre-compute embeddings for all artifacts on `skillmeat sync`
- Update incrementally on `skillmeat add`
- Store in `~/.skillmeat/cache/embeddings.db`

**Performance**: ~50ms for query over 1000 artifacts (dominated by SQLite read, not inference).

---

## Fallback Strategy

If sentence-transformers unavailable (missing dependencies, etc.):

**Fallback 1**: TF-IDF + BM25 (traditional text search)
- No ML dependencies
- Fast (~10ms)
- Decent quality for keyword-based queries
- Implementation: Use `scikit-learn` TfidfVectorizer or pure Python BM25

**Fallback 2**: Fuzzy string matching
- Levenshtein distance on artifact names/descriptions
- No dependencies (Python stdlib or `rapidfuzz`)
- Poor semantic understanding but better than nothing

**Auto-detection**:
```python
try:
    from sentence_transformers import SentenceTransformer
    USE_EMBEDDINGS = True
except ImportError:
    logger.warning("sentence-transformers not installed, falling back to TF-IDF")
    USE_EMBEDDINGS = False
```

---

## Cost & Performance Comparison

| Approach | Offline | Latency (per query) | Cost | Memory | Quality |
|----------|---------|-------------------|------|--------|---------|
| **sentence-transformers** | ✅ | 10-50ms | $0 | 100MB | ★★★★☆ |
| Haiku skill | ❌ | 500ms+ | ~$0.001/query | 0MB | ★★★★★ (hypothetical) |
| OpenAI API | ❌ | 100-300ms | $0.00002/artifact | 0MB | ★★★★★ |
| TF-IDF fallback | ✅ | 10ms | $0 | <10MB | ★★★☆☆ |

---

## Conclusion

**Primary**: Local sentence-transformers (`all-MiniLM-L6-v2`) with SQLite caching.

**Fallback**: TF-IDF or BM25 if ML dependencies unavailable.

**Not Recommended**: API-based embeddings (OpenAI/Cohere) for CLI use case due to latency, cost, and offline requirement.

**Next Steps**:
1. Add `sentence-transformers` to optional dependencies: `pip install skillmeat[search]`
2. Implement `EmbeddingService` in `skillmeat/core/search/`
3. Integrate with `skillmeat search` command
4. Add embedding cache to `.gitignore` and cleanup on `skillmeat sync --clean`
