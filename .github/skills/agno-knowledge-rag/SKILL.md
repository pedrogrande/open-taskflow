---
name: agno-knowledge-rag
description: 'Configure Agno Knowledge bases and RAG pipelines — vector stores, readers, chunking, embedders, filters, agentic RAG, traditional RAG, custom retrievers, and knowledge for agents and teams. Use when an agent needs domain-specific documents, when building semantic search, when ingesting PDFs/URLs/CSVs, when filtering knowledge by metadata, or when sharing vector databases across multiple agents.'
argument-hint: 'Knowledge purpose and content source, e.g. "product docs KB — PDFs + URLs with per-user filtering"'
user-invocable: true
---

# Agno Knowledge & RAG

Configure knowledge bases that give agents access to domain-specific content beyond their training data. Covers the full knowledge lifecycle: ingestion (readers), processing (chunking, embedding), storage (vector databases), retrieval (agentic RAG, traditional RAG, filters), and isolation (multi-tenant).

## When to Use

- Agent needs domain-specific documents (product docs, schemas, FAQs)
- Building semantic search over a document corpus
- Ingesting PDFs, URLs, CSVs, Markdown, or other content
- Filtering knowledge by metadata (per-user, per-department)
- Sharing a vector database across multiple agents (isolation)
- Agent should learn and save insights across conversations
- Team needs coordinated or distributed RAG

## How It Works

```
Content → Reader → Chunker → Embedder → Vector DB
                                              ↓
Query → Embedder → Vector Search → Relevant Chunks → Agent Context
```

Three components:
1. **Content ingestion**: Readers parse files, URLs, or raw text
2. **Chunking & embedding**: Documents split into chunks, converted to vectors
3. **Search & retrieval**: Agent searches vector DB, includes results in context

## Procedure

### 1. Choose the Vector Database

| Database | Use Case | Setup |
|----------|----------|-------|
| **SurrealDB** | This project's default | `db/session.py` → `create_surrealdb_knowledge()` |
| **PgVector** | Production, hybrid search, SQL access | Needs PostgreSQL + pgvector extension |
| **LanceDB** | Local dev, zero setup | File-based, no server needed |
| **ChromaDB** | Local dev, open-source | In-memory or persistent |
| **Pinecone** | Managed, auto-scaling | Cloud service, no ops |
| **Qdrant** | High performance, hybrid search | Self-hosted or cloud |
| **Milvus/Zilliz** | Large scale, distributed | This project's docs collection |

**For this project**, use `create_surrealdb_knowledge()`:

```python
from db import create_surrealdb_knowledge

my_kb = create_surrealdb_knowledge("My Knowledge", "my_vectors")
```

This creates a `Knowledge` instance with SurrealDB vector store and `text-embedding-3-small` embedder.

### 2. Create the Knowledge Base

**Using the project helper (SurrealDB):**

```python
from db import create_surrealdb_knowledge

knowledge = create_surrealdb_knowledge("Product Docs", "product_vectors")
```

**Custom configuration:**

```python
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.surrealdb import SurrealDb as SurrealVectorDb
from agno.db.surrealdb import SurrealDb
from surrealdb import Surreal
from db.url import SURREALDB_URL, surrealdb_credentials, SURREALDB_NAMESPACE, SURREALDB_DATABASE

client = Surreal(url=SURREALDB_URL)
client.signin(surrealdb_credentials)
client.use(namespace=SURREALDB_NAMESPACE, database=SURREALDB_DATABASE)

knowledge = Knowledge(
    name="Product Docs",
    vector_db=SurrealVectorDb(
        client=client,
        collection="product_vectors",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        efc=150,        # HNSW build time/accuracy trade-off
        m=12,           # HNSW max connections per element
        search_ef=40,   # HNSW search time/accuracy trade-off
    ),
)
```

**With a contents database** (tracks metadata, enables agentic filters):

```python
from db import get_surrealdb

knowledge = Knowledge(
    name="Product Docs",
    vector_db=SurrealVectorDb(client=client, collection="product_vectors"),
    contents_db=get_surrealdb(table_name="knowledge_contents"),
)
```

### 3. Load Content

**From a URL:**

```python
knowledge.insert(
    url="https://docs.example.com/guide.pdf",
    metadata={"department": "engineering"},
)
```

**From a file path:**

```python
knowledge.insert(
    path="docs/product/",
    metadata={"version": "2.0"},
)
```

**From raw text:**

```python
knowledge.insert(
    name="API Reference",
    text_content="The API supports REST and GraphQL endpoints...",
)
```

**Async (for batch operations):**

```python
await knowledge.ainsert(url="https://docs.example.com/guide.pdf")
await knowledge.ainsert(path="docs/product/", skip_if_exists=True)
```

**Skip already-processed files:**

```python
knowledge.insert(
    path="documents/",
    skip_if_exists=True,  # Don't reprocess existing files
    include=["*.pdf", "*.md"],
    exclude=["*temp*", "*draft*"],
)
```

### 4. Choose a Reader

Readers parse content into `Document` objects. Agno auto-selects based on file extension.

| Reader | Format | Import |
|--------|--------|--------|
| `PDFReader` | PDF files | `agno.knowledge.reader.pdf_reader` |
| `CSVReader` | CSV files | `agno.knowledge.reader.csv_reader` |
| `MarkdownReader` | Markdown | `agno.knowledge.reader.markdown_reader` |
| `JSONReader` | JSON files | `agno.knowledge.reader.json_reader` |
| `TextReader` | Plain text | `agno.knowledge.reader.text_reader` |
| `DoclingReader` | Multi-format | `agno.knowledge.reader.docling_reader` |
| `WebsiteReader` | Web crawl | `agno.knowledge.reader.website_reader` |
| `ArxivReader` | Academic papers | `agno.knowledge.reader.arxiv_reader` |
| `WikipediaReader` | Wikipedia | `agno.knowledge.reader.wikipedia_reader` |
| `YouTubeReader` | YouTube transcripts | `agno.knowledge.reader.youtube_reader` |

**Override the auto-selected reader:**

```python
from agno.knowledge.reader.pdf_reader import PDFReader

reader = PDFReader(chunk_size=3000, split_on_pages=True)
knowledge.insert(path="documents/", reader=reader)
```

### 5. Choose a Chunking Strategy

Chunking splits documents into smaller pieces for precise retrieval.

| Strategy | Best For | Speed | Quality |
|----------|----------|-------|---------|
| **Semantic** | Complex documents, maintain meaning | Slower | Best |
| **Fixed Size** | Uniform content, predictable chunks | Fast | Good |
| **Recursive** | Structured docs, multiple separators | Fast | Good |
| **Document** | Preserve sections/pages | Fast | Good |
| **Markdown** | Heading-structured content | Fast | Good |
| **CSV Row** | Tabular data | Fast | Good |
| **Code** | Source code (AST-aware) | Medium | Good |
| **Agentic** | AI determines optimal boundaries | Slowest | Adaptive |

**Pass chunking strategy to a reader:**

```python
from agno.knowledge.chunking.semantic_chunking import SemanticChunking
from agno.knowledge.reader.pdf_reader import PDFReader

reader = PDFReader(chunking_strategy=SemanticChunking(similarity_threshold=0.7))
knowledge.insert(path="documents/", reader=reader)
```

**Chunk size guidelines:**

| Size | Trade-off |
|------|-----------|
| Small (1000-3000 chars) | More precise retrieval, may lose context |
| Default (5000 chars) | Balanced precision and context |
| Large (8000+ chars) | More context, less targeted results |

### 6. Choose an Embedder

Embedders convert text to vectors. The default is `OpenAIEmbedder(id="text-embedding-3-small")`.

| Embedder | Type | Cost | Notes |
|----------|------|------|-------|
| **OpenAI** | Hosted | $$ | Default, excellent quality |
| **Gemini** | Hosted | $$ | Multilingual, Google ecosystem |
| **Cohere** | Hosted | $$ | Strong retrieval |
| **Ollama** | Local | Free | Privacy, offline |
| **FastEmbed** | Local | Free | Fast local embeddings |
| **Voyage AI** | Hosted | $$$ | Best retrieval quality |

**⚠️ Vectors from different embedders are NOT compatible.** If you switch embedders, you must re-embed all content.

**Configure the embedder:**

```python
from agno.knowledge.embedder.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(
    id="text-embedding-3-small",
    dimensions=1536,
    enable_batch=True,   # Batch API calls
    batch_size=100,      # 100 texts per call
)
```

### 7. Add Knowledge to an Agent

**Agentic RAG (default)** — agent decides when to search:

```python
from agno.agent import Agent
from app.settings import default_model
from db import get_surrealdb, create_surrealdb_knowledge

product_kb = create_surrealdb_knowledge("Product Docs", "product_vectors")

agent = Agent(
    id="support-agent",
    name="Support Agent",
    model=default_model(),
    db=get_surrealdb(),
    knowledge=product_kb,
    search_knowledge=True,  # Adds search_knowledge_base() tool (default when knowledge is set)
)
```

**Traditional RAG** — always inject context into prompt:

```python
agent = Agent(
    knowledge=product_kb,
    search_knowledge=False,           # Don't add search tool
    add_knowledge_to_context=True,    # Always inject relevant context
)
```

**When to use which:**

| Approach | When | Token Cost |
|----------|------|-----------|
| Agentic RAG | Agent decides when to search | Low — only searches when needed |
| Traditional RAG | Every query needs context | High — always injects context |

### 8. Add Filters

Filters restrict searches to documents matching metadata criteria.

**Manual filters** — set at agent or query level:

```python
# Agent-level filter (applies to all searches)
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
    knowledge_filters={"department": "engineering"},
)

# Query-level filter (overrides agent-level)
agent.run("How do I deploy?", knowledge_filters={"version": "2.0"})

# Direct search with filters
results = knowledge.search(
    query="deployment process",
    filters={"department": "engineering", "year": 2025},
)
```

**Agentic filters** — agent infers filters from the query:

```python
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
    enable_agentic_knowledge_filters=True,  # Agent extracts filters from query
)
# User asks: "What are Jordan's skills?"
# Agent automatically adds filter: {"user_id": "jordan_mitchell"}
```

**Add metadata when inserting:**

```python
knowledge.insert(
    path="resumes/",
    metadata={"user_id": "jordan_mitchell", "document_type": "cv", "year": 2025},
)
```

### 9. Isolate Vector Search (Multi-Tenant)

When multiple Knowledge instances share one vector database, set `isolate_vector_search=True` to scope searches:

```python
from db import create_surrealdb_knowledge

# Both use the same SurrealDB, but searches are isolated
hr_kb = create_surrealdb_knowledge("HR Docs", "shared_vectors")
hr_kb.isolate_vector_search = True

eng_kb = create_surrealdb_knowledge("Engineering Docs", "shared_vectors")
eng_kb.isolate_vector_search = True
```

**⚠️ Enabling isolation on existing data:** Documents indexed before `isolate_vector_search` was set don't have `linked_to` metadata. They'll be invisible to isolated searches. Re-index or manually update metadata.

### 10. Custom Retriever

For complete control over search logic:

```python
from typing import Optional
from agno.agent import Agent

def knowledge_retriever(agent: Agent, query: str, num_documents: Optional[int] = None, **kwargs) -> Optional[list[dict]]:
    """Custom retrieval logic."""
    # Your search logic here
    results = knowledge.search(query=query, limit=num_documents or 5)
    return [{"content": r.content, "meta_data": r.meta_data} for r in results]

agent = Agent(
    knowledge=knowledge,
    knowledge_retriever=knowledge_retriever,
    search_knowledge=True,
)
```

### 11. Knowledge for Teams

**Leader-level knowledge** — leader searches to inform delegation:

```python
team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    knowledge=product_kb,
    search_knowledge=True,
)
```

**Distributed RAG** — each member has its own knowledge base:

```python
news_kb = create_surrealdb_knowledge("News KB", "news_vectors")
finance_kb = create_surrealdb_knowledge("Finance KB", "finance_vectors")

news_agent = Agent(name="News Agent", knowledge=news_kb, search_knowledge=True)
finance_agent = Agent(name="Finance Agent", knowledge=finance_kb, search_knowledge=True)
```

### 12. Agent Learns and Saves Knowledge

Agents can write to the knowledge base, building expertise over time:

```python
def save_learning(title: str, insight: str) -> str:
    """Save a reusable insight to the knowledge base."""
    knowledge.insert(name=title, text_content=insight)
    return f"Saved: {title}"

agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,
    tools=[save_learning],
    update_knowledge=True,  # Adds update_knowledge tool
)
```

### 13. Register in AgentOS

Knowledge bases are attached to agents, not registered separately. Just add the agent:

```python
# app/main.py
from db import create_surrealdb_knowledge

product_kb = create_surrealdb_knowledge("Product Docs", "product_vectors")
# Load content at startup or via a seed script
product_kb.insert(path="docs/product/")

support_agent = Agent(
    id="support-agent",
    knowledge=product_kb,
    search_knowledge=True,
    # ... rest of agent config
)

agent_os = AgentOS(agents=[..., support_agent], ...)
```

## Common Patterns for This Project

### Database
- **Vector store**: `create_surrealdb_knowledge(name, collection)` from `db/session.py`
- **Embedder**: `OpenAIEmbedder(id="text-embedding-3-small")` — configured in the helper
- **Session storage**: `get_surrealdb()` — same SurrealDB instance, different tables

### SurrealDB HNSW Parameters
When creating a custom `SurrealVectorDb`, tune these:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `efc` | 150 | Build time/accuracy (higher = better index, slower build) |
| `m` | 12 | Max connections per element (higher = better recall, more memory) |
| `search_ef` | 40 | Search time/accuracy (higher = better results, slower search) |

### Content Loading Strategy
- **Startup**: Load critical docs in `app/main.py` lifespan or seed scripts
- **On-demand**: Use `knowledge.insert()` in agent tools when new content arrives
- **Batch**: Use `knowledge.insert(path="...", skip_if_exists=True)` for large corpora

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Search returns no results | No content loaded, or wrong collection | Call `knowledge.insert()` before searching |
| Search returns irrelevant results | Wrong chunking strategy or chunk size too large | Try `SemanticChunking` or smaller `chunk_size` |
| Embedding errors | API key not set for embedder | Set `OPENAI_API_KEY` in `.env` |
| SurrealDB connection fails | Wrong URL or credentials | Check `SURREALDB_URL`, `SURREALDB_USER`, `SURREALDB_PASS` |
| Filters have no effect | No metadata on documents | Add `metadata={}` when calling `knowledge.insert()` |
| Isolated search returns nothing | Existing data lacks `linked_to` metadata | Re-index content after enabling `isolate_vector_search` |
| Slow batch ingestion | No async, no batch embeddings | Use `await knowledge.ainsert()` + `enable_batch=True` |
| Wrong embedder dimensions | Mismatch between embedder and vector DB | Ensure `dimensions=1536` matches `text-embedding-3-small` |
| Switched embedders, search broken | Vectors from different embedders incompatible | Re-embed all content with new embedder |

## Related Resources

- [Agno knowledge overview](https://docs.agno.com/knowledge/overview) — concepts, workflow, examples
- [Agno agents with knowledge](https://docs.agno.com/knowledge/agents/overview) — agentic RAG, traditional RAG
- [Agno vector databases](https://docs.agno.com/knowledge/concepts/vector-db) — 20+ supported databases
- [Agno SurrealDB vector store](https://docs.agno.com/knowledge/vector-stores/surrealdb/overview) — this project's default
- [Agno chunking strategies](https://docs.agno.com/knowledge/concepts/chunking/overview) — 8 strategies
- [Agno embedders](https://docs.agno.com/knowledge/concepts/embedder/overview) — 15+ embedders
- [Agno readers](https://docs.agno.com/knowledge/concepts/readers/overview) — 15+ readers
- [Agno knowledge filters](https://docs.agno.com/knowledge/concepts/filters/overview) — manual & agentic
- [Agno isolate vector search](https://docs.agno.com/knowledge/concepts/isolate-vector-search) — multi-tenant isolation
- [Agno performance tips](https://docs.agno.com/knowledge/concepts/performance-tips) — optimization guide
- [Agno teams with knowledge](https://docs.agno.com/knowledge/teams/overview) — distributed RAG
- Project: `db/session.py` — `create_surrealdb_knowledge()` helper
- Project: `db/url.py` — SurrealDB connection config
- Project: `create-agno-agent` skill — adding knowledge to agents
- Project: `create-agno-team` skill — team-level and distributed knowledge