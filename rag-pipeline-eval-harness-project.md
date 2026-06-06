# RAG Pipeline Evaluation Harness

## Project Specification v0.1

***

## 1. Problem Statement

Building a production RAG system requires choosing across at least **four independent axes** — extraction method, chunking strategy, embedding model, and vector store — but most evaluation work only isolates one axis at a time, and rarely with consistent infrastructure. This project builds a **systematic, reproducible evaluation harness** that treats each axis as a swappable module, enabling controlled experiments that produce genuinely comparable results.

***

## 2. Goals

**Primary:** Determine which combination of vector store + pipeline configuration produces the best retrieval quality for a corpus of PDF research papers, using Agno as the agent framework.

**Secondary:**

- Establish a reusable harness for future pipeline configuration comparisons
- Generate benchmark data useful for Zero Team consulting practice
- Learn the real operational tradeoffs (cost, complexity, latency) of each vector store in a local Docker environment

***

## 3. The Four Testable Axes

The key insight is that these are **orthogonal dimensions** — each can vary independently. The harness treats them as a matrix, not a fixed pipeline.

### Axis 1 — Extraction Method

How raw PDF content is converted into structured text.

| ID | Tool | Output | Notes |
|---|---|---|---|
| `extract.pymupdf` | PyMuPDF4LLM | Flat Markdown | Fast baseline; poor on multi-column |
| `extract.docling` | Docling (IBM) | Typed JSON + Markdown | Layout-aware ML model; good for research papers  [github](https://github.com/docling-project/docling) |
| `extract.unstructured` | Unstructured.io `hi_res` | Typed JSON elements | Best table/figure recovery; slowest  [unstructured](https://unstructured.io/blog/how-to-process-pdf-in-python) |

### Axis 2 — Chunking Strategy

How extracted content is split into indexable units.

| ID | Strategy | Description |
|---|---|---|
| `chunk.fixed` | Fixed-size token | 512 tokens, 10% overlap — simple baseline  [milvus](https://milvus.io/ai-quick-reference/what-is-the-optimal-chunk-size-for-rag-applications) |
| `chunk.recursive` | Recursive/structural | Split by section → paragraph → sentence |
| `chunk.semantic` | Semantic boundary | Embedding-similarity-based split points  [weaviate](https://weaviate.io/blog/chunking-strategies-for-rag) |
| `chunk.hierarchical` | Parent-child | 1024-token parent + 256-token child; returns parent context on hit |

### Axis 3 — Embedding Model

What model converts chunks to vectors. All dimensions fixed for fair vector store comparison.

| ID | Model | Dims | Cost | Notes |
|---|---|---|---|---|
| `embed.openai-small` | `text-embedding-3-small` | 768 | API | Good quality/cost ratio  [tigerdata](https://www.tigerdata.com/blog/open-source-vs-openai-embeddings-for-rag) |
| `embed.openai-large` | `text-embedding-3-large` | 1536 | API (3×) | Best OpenAI quality |
| `embed.nomic` | `nomic-embed-text-v1.5` | 768 | Free/local | Strong open-source baseline |
| `embed.fastembed` | `BAAI/bge-small-en-v1.5` | 384 | Free/local | Fastest dev iteration |

### Axis 4 — Vector Store

Where embeddings are stored and retrieved from.

| ID | Store | Type |
|---|---|---|
| `store.pgvector` | PgVector | SQL-based |
| `store.surrealdb` | SurrealDB | NoSQL/multi-model |
| `store.qdrant` | Qdrant | Dedicated |
| `store.lancedb` | LanceDB | Local embedded |
| `store.chroma` | Chroma | Local embedded |

***

## 4. Modular Architecture

The key architectural principle: **each axis is a protocol with swappable implementations**, not a hardcoded class. A pipeline configuration is just a dict of four IDs.

```
PipelineConfig(
    extract = "extract.docling",
    chunk   = "chunk.recursive",
    embed   = "embed.nomic",
    store   = "store.qdrant"
)
```

```
┌─────────────────────────────────────────────────────┐
│                   INGESTION PIPELINE                 │
│                                                      │
│  PDF ──► [Extractor] ──► [Chunker] ──► [Embedder]  │
│               ▲               ▲             ▲        │
│         Registry         Registry       Registry     │
│         (pluggable)      (pluggable)   (pluggable)  │
│                                             │        │
│                                        [VectorDB]   │
│                                             ▲        │
│                                          Registry   │
│                                         (pluggable) │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                  AGNO AGENT LAYER                    │
│                                                      │
│  build_eval_agent(config: PipelineConfig) → Agent   │
│                                                      │
│  Same model, same instructions, same query set       │
│  Only the knowledge.vector_db differs per agent     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                 EVALUATION LAYER (DeepEval)          │
│                                                      │
│  ContextualRecall    — did we retrieve what matters? │
│  ContextualPrecision — was retrieved content ranked? │
│  ContextualRelevancy — were chunks the right size?   │
│  Faithfulness        — did answer match retrieved?   │
│  AnswerRelevancy     — was answer useful?            │
│  Latency / IngestTime — operational costs            │
└─────────────────────────────────────────────────────┘
```

### The Registry Pattern

```python
# pipeline/registry.py

EXTRACTORS: dict[str, type[BaseExtractor]] = {
    "extract.pymupdf":       PyMuPDFExtractor,
    "extract.docling":       DoclingExtractor,
    "extract.unstructured":  UnstructuredExtractor,
}

CHUNKERS: dict[str, type[BaseChunker]] = {
    "chunk.fixed":           FixedTokenChunker,
    "chunk.recursive":       RecursiveChunker,
    "chunk.semantic":        SemanticChunker,
    "chunk.hierarchical":    HierarchicalChunker,
}

EMBEDDERS: dict[str, type[BaseEmbedder]] = {
    "embed.openai-small":    OpenAIEmbedder,
    "embed.nomic":           NomicEmbedder,
    "embed.fastembed":       FastEmbedEmbedder,
}

STORES: dict[str, type[BaseVectorStore]] = {
    "store.pgvector":        PgVectorStore,
    "store.qdrant":          QdrantStore,
    "store.surrealdb":       SurrealDBStore,
    "store.lancedb":         LanceDBStore,
    "store.chroma":          ChromaStore,
}

def build_pipeline(config: PipelineConfig) -> IngestionPipeline:
    return IngestionPipeline(
        extractor = EXTRACTORS[config.extract](),
        chunker   = CHUNKERS[config.chunk](),
        embedder  = EMBEDDERS[config.embed](),
        store     = STORES[config.store](),
    )
```

Every new extractor, chunker, or store is **one new class + one registry entry**. No other changes needed.

***

## 5. Experiment Design

### Phase 1 — Store Baseline (Fix Everything Except Store)

Hold extraction, chunking, and embedding constant. Vary only the vector store.

```
extract.docling × chunk.recursive × embed.nomic × [all 5 stores]
```

This answers: **"Which store performs best, all else equal?"**

### Phase 2 — Chunking Sensitivity (Fix Store, Vary Chunking)

Pick the best store from Phase 1. Vary chunking strategy.

```
extract.docling × [all 4 chunkers] × embed.nomic × store.qdrant
```

This answers: **"How much does chunking strategy matter?"**

### Phase 3 — Extraction Comparison (Fix Store + Chunking, Vary Extraction)

Vary the extractor.

```
[all 3 extractors] × chunk.recursive × embed.nomic × store.qdrant
```

This answers: **"How much does extraction quality affect retrieval?"**

### Phase 4 — Embedding Sensitivity

Vary the embedder (and rebuild all indexes).

```
extract.docling × chunk.recursive × [all 4 embedders] × store.qdrant
```

This answers: **"Does a free local embedder rival OpenAI for this corpus?"**

***

## 6. Evaluation Metrics

Using **DeepEval** as the evaluation layer, which maps directly onto the retrieval/generation split: [deepeval](https://deepeval.com/guides/guides-rag-evaluation)

### Retrieval Metrics (per config, per query)

- **Contextual Recall** — fraction of ground truth answer covered by retrieved chunks [machinelearningmastery](https://machinelearningmastery.com/understanding-rag-part-iv-ragas-evaluation-framework/)
- **Contextual Precision** — proportion of retrieved chunks that were actually relevant [deepeval](https://deepeval.com/guides/guides-rag-evaluation)
- **Contextual Relevancy** — whether chunk size/top-K returned the right density [deepeval](https://deepeval.com/guides/guides-rag-evaluation)
- **Hit Rate** — % of queries where at least one correct chunk was retrieved
- **Ingest Time (ms)** — time to extract + chunk + embed + load for the full corpus

### Generation Metrics (per config, per query)

- **Faithfulness** — does the answer only use retrieved context, no hallucination [machinelearningmastery](https://machinelearningmastery.com/understanding-rag-part-iv-ragas-evaluation-framework/)
- **Answer Relevancy** — is the answer actually responsive to the question [deepeval](https://deepeval.com/guides/guides-rag-evaluation)
- **Query Latency (ms)** — agent.arun() wall time

### Operational Metrics (per config)

- **Embedding API cost ($)** — token count × model rate
- **Index storage size (MB)**
- **Docker memory footprint (MB)**

***

## 7. Query Set Design

Queries span four categories to stress-test different pipeline properties:

| Category | Example | Tests |
|---|---|---|
| **Factual** | "What accuracy did method X achieve?" | Precision, exact chunk retrieval |
| **Relational** | "How does approach A differ from B?" | Multi-chunk synthesis |
| **Multi-hop** | "What motivated the design choice in section 3?" | Cross-section retrieval, hierarchical chunking |
| **Edge case** | Query about a table's data | Table extraction, non-prose chunking |

Ground truth Q&A pairs are generated from chunks using an LLM, then manually reviewed before use in any evaluation run.

***

## 8. Recommended Open Source Tool Stack

| Role | Tool | Why |
|---|---|---|
| Agent framework | **Agno 2.6.9** | Core requirement; Knowledge base abstraction |
| PDF extraction | **Docling** | Layout-aware, JSON + MD output, local  [github](https://github.com/docling-project/docling) |
| Evaluation | **DeepEval** | Best retrieval-specific metrics; unit-test pattern  [deepeval](https://deepeval.com/guides/guides-rag-evaluation) |
| Ground truth gen | **RAGAS** (via DeepEval) | Integrates RAGAS metrics into DeepEval test cases  [deepeval](https://deepeval.com/docs/metrics-ragas) |
| Local embeddings | **FastEmbed** (BAAI/bge) | Zero API cost for dev iteration |
| CLI | **Typer** | Already in your stack pattern |
| Results storage | **SurrealDB** | Store all EvalResult records; query across runs |
| Visualisation | **Plotly / Pandas** | Export comparison charts per phase |

***

## 9. Revised Project Structure

```
rag-eval/
├── pipeline/
│   ├── registry.py          # All four registries
│   ├── config.py            # PipelineConfig dataclass
│   ├── extractors/
│   │   ├── base.py          # BaseExtractor protocol
│   │   ├── pymupdf.py
│   │   ├── docling.py
│   │   └── unstructured.py
│   ├── chunkers/
│   │   ├── base.py          # BaseChunker protocol
│   │   ├── fixed.py
│   │   ├── recursive.py
│   │   ├── semantic.py
│   │   └── hierarchical.py
│   ├── embedders/
│   │   ├── base.py          # BaseEmbedder protocol
│   │   ├── openai.py
│   │   ├── nomic.py
│   │   └── fastembed.py
│   └── stores/
│       ├── base.py          # BaseStore protocol
│       ├── pgvector.py
│       ├── qdrant.py
│       ├── surrealdb.py
│       ├── lancedb.py
│       └── chroma.py
├── agents/
│   └── eval_agent.py        # build_eval_agent(config) → Agent
├── eval/
│   ├── queries.py           # Query dataclass + query set
│   ├── ground_truth.py      # LLM Q&A pair generator
│   ├── runner.py            # run_experiment(configs, queries)
│   └── metrics.py           # DeepEval metric wrappers
├── experiments/
│   ├── phase1_stores.py     # Phase 1 experiment definition
│   ├── phase2_chunking.py
│   ├── phase3_extraction.py
│   └── phase4_embedding.py
├── results/                 # CSV + charts per run
├── dataset/                 # PDF corpus
├── compose.yaml
└── pyproject.toml
```

***

## 10. Key Constraints & Decisions

- **All infrastructure runs locally in Docker** — no cloud vector DB services during eval (cost + reproducibility)
- **Agno Knowledge base abstraction** used for all stores — no direct DB client calls in agent layer
- **Same Agno agent spec** for all configs — model, instructions, top-k, temperature are constants
- **SurrealDB as eval results store** — all `EvalResult` records written there, queryable across runs
- **DeepEval as evaluation layer** — not custom metrics, to ensure methodology is defensible and reproducible [deepeval](https://deepeval.com/guides/guides-rag-evaluation)
- **Docling as default extractor** — best fit for research paper corpus; PyMuPDF kept as fast baseline

***

## 11. Open Questions (to resolve before implementation)

1. **Corpus size** — how many papers? (10 for fast iteration, 50+ for meaningful results)
2. **Experiment scope** — run full 4-phase matrix or start with Phase 1 only?
3. **Dimensions for embed.openai-small** — 768 or 1536? (affects storage cost for all 5 stores)
4. **Ground truth review** — LLM-generated only, or manually reviewed before Phase 1 begins?
5. **Results presentation** — internal tool only, or publishable benchmark (affects how ground truth and methodology are documented)?
