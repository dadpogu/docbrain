# System Deployment & Configuration Guide

## Current target: connect to hosted services

Follow the [implementation plan](../plans/implementation_plan.md) for the current design. LiteLLM, Docling or LiteParse, Qdrant, and Memgraph are provided services. Deploy DocBrain's API and worker from this repository; do not deploy replacement databases or administer provider infrastructure as a side effect of starting the application.

**Status:** application packaging, endpoints, migrations, and commands are planned, not implemented. The historical examples later in this document do not constitute a working deployment recipe.

Process documentation (Compliance Agent, Documentation Agent, site-specific policies and procedures) is a separate future application; see [process_pipeline_future](../plans/process_pipeline_future/README.md).

### Ownership and required access

| Dependency | Supplied by operator | DocBrain responsibility |
| --- | --- | --- |
| LiteLLM | TLS endpoint, restricted application key, model aliases, quotas | LangChain integration, structured-output validation, bounded calls, usage tracking. Never require the gateway master key. |
| Parser | Endpoint, authentication, engine/version, request/job protocol | Normalize output, preserve source coordinates, enforce file/page limits, record parser profile. |
| Qdrant | Endpoint, restricted API key, environment namespace | Explicit versioned collection/index migrations; filtered reads/writes and embedding-profile validation. |
| Memgraph | Bolt/TLS endpoint, credentials, supported version/procedures | Memgraph-specific migrations and queries, bounded traversal, capability-gated MAGE jobs. No assumption of Neo4j APOC or GDS. |
| PostgreSQL (proposed) | Database, application/migration roles, backup policy | Registry, durable jobs, audit/approval records, LangGraph checkpoint schema. |
| Artifact storage | Bucket/prefix or development directory, retention policy | Immutable artifacts, checksums, authorized source access, cleanup ledger. |
| Identity/telemetry | Trusted identity configuration, optional OTLP endpoint | Request authorization, trace redaction, health/readiness and operational metrics. |

### Proposed application settings

These are configuration contract names to implement in Phase 0, not settings consumed by today's reference modules. Secrets are injected by the operator's secret manager. `.env.example` will contain empty secret values, and `.env` must be excluded from Git before it is created.

| Group | Settings |
| --- | --- |
| Environment | `DOCBRAIN_ENV`, `LOG_LEVEL`, `SERVICE_NAMESPACE` |
| Models | `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `MODEL_ROUTER`, `MODEL_EXTRACTOR`, `MODEL_SUMMARIZER`, `MODEL_ANSWER`, `MODEL_EMBEDDING`, optional `MODEL_RERANKER` |
| Embedding profile | `EMBEDDING_PROFILE`, `EMBEDDING_DIMENSION`, `SPARSE_MODEL`; validate against actual responses and collection configuration |
| Parser | `PARSER_PROVIDER` (`docling` or `liteparse`), `PARSER_BASE_URL`, `PARSER_API_KEY`, `PARSER_PROFILE` |
| Vector index | `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_CHUNK_COLLECTION`, `QDRANT_SEMANTIC_COLLECTION` |
| Graph | `GRAPH_PROVIDER=memgraph`, `GRAPH_URI`, `GRAPH_USERNAME`, `GRAPH_PASSWORD`; TLS behavior tested against the supplied endpoint |
| Durable state | `DATABASE_URL`; separate administrator credentials used only by explicit migrations |
| Artifacts | `ARTIFACT_BACKEND`, `ARTIFACT_ROOT` or `ARTIFACT_BUCKET`/`ARTIFACT_PREFIX`; prefer workload identity for hosted access |
| Identity | `AUTH_ISSUER`, `AUTH_AUDIENCE`; local development identity only in an explicit non-shared mode |
| Limits | `REQUEST_TIMEOUT_SECONDS`, `JOB_MAX_ATTEMPTS`, `WORKER_CONCURRENCY`, `MAX_UPLOAD_BYTES`, `MAX_DOCUMENT_PAGES`, `QUERY_TOKEN_BUDGET` |
| Telemetry | Optional `OTEL_EXPORTER_OTLP_ENDPOINT`; document/prompt capture disabled by default |

Provider replacement requires passing adapter contract tests and migrating incompatible data. Do not advertise unsupported providers in settings before adapters exist. Keep model credentials, TLS policies, data residency, quotas, and retry behavior explicit; do not silently fall back to an unapproved public endpoint.

### Release sequence

1. Install the locked application environment and validate settings without mutations. Confirm parser and model capability profiles and read-only service connectivity.
2. Provision isolated staging namespaces through the service owner. Use disposable fixtures for write probes; never infer permission to write into existing production collections.
3. Review migration plans for Postgres, Qdrant, and Memgraph. Apply with an operator-authorized migration role, not on API startup. Runtime credentials are less privileged.
4. Run adapter contracts, then ingestion/publication/query/citation/rollback tests against the actual service versions. Exercise worker interruption, stale approvals, and provider failure.
5. Start the API and separate worker. LangGraph runs in these processes; PostgreSQL provides job leases and checkpoints. Redis/Celery and a hosted agent platform are not initial requirements.
6. Ingest a canary corpus, inspect its evidence, compare evaluation results, and publish its validated manifest. Increase load only after latency, cost, and scope-isolation gates pass.
7. Obtain authorization for shared deployment/cutover. Retain the previous compatible application version and manifest; schema rollback must respect retained data and cannot revive revoked access.

Health checks must distinguish liveness, required-dependency readiness, and optional enrichment availability. Do not perform paid model generations on every readiness probe. Operational dashboards track queue age, stage failures, unpublished builds, citation resolution errors, dependency latency, and per-run cost.

Back up the registry, checkpoint state, and immutable artifacts. Test restoring citation resolution and resumable jobs; vector/graph snapshots alone are insufficient. For model/index changes, build a parallel profile, validate it, and switch manifests rather than overwriting the old embedding space.

## Historical self-hosting examples — not current instructions

The remaining sections preserve the earlier Neo4j/Celery/self-hosting design for reference only. Their container tags, credentials, plugin assumptions, latency expectations, configuration fields, and commands have not been validated for the current project. Referenced application modules and Dockerfiles may not exist. Do not copy these examples into production; the hosted-service contract above supersedes them. No real credentials should be stored in this document.

---

## 1. Architecture Topology & Network Connections

```mermaid
graph TD
    classDef client fill:#2563eb,stroke:#1d4ed8,color:#ffffff;
    classDef svc fill:#d97706,stroke:#b45309,color:#ffffff;
    classDef db fill:#059669,stroke:#047857,color:#ffffff;

    CLIENT["Agent / Client Application"]:::client
    BROKER["Retrieval Broker (Port 8000)"]:::svc
    INGEST["Ingestion Worker (Celery / Background)"]:::svc
    LITELLM["LiteLLM Proxy (Port 4000)"]:::svc

    QDRANT[("Qdrant Vector DB (Port 6333 / 6334)")]:::db
    NEO4J[("Neo4j Graph DB (Bolt Port 7687)")]:::db
    REDIS[("Redis Cache & Queue (Port 6379)")]:::db
    OBS[("Langfuse Observability (Port 3000)")]:::db

    CLIENT --> BROKER
    CLIENT --> LITELLM
    
    BROKER --> QDRANT
    BROKER --> NEO4J
    BROKER --> REDIS
    BROKER --> LITELLM
    BROKER --> OBS

    INGEST --> REDIS
    INGEST --> LITELLM
    INGEST --> QDRANT
    INGEST --> NEO4J
    INGEST --> OBS
```

---

## 2. Master Environment Variables (`.env.example`)

Create a root `.env` file or populate your secrets manager / Kubernetes `Secret` / `ConfigMap` with the following variables:

```bash
# ==============================================================================
# 1. CORE ENVIRONMENT & NETWORKING
# ==============================================================================
ENV=production                             # development | staging | production
LOG_LEVEL=INFO                             # DEBUG | INFO | WARNING | ERROR
SERVICE_TIMEOUT_SECONDS=30

# ==============================================================================
# 2. LITELLM PROXY (MODEL GATEWAY)
# ==============================================================================
LITELLM_HOST=0.0.0.0
LITELLM_PORT=4000
LITELLM_BASE_URL=http://litellm-proxy:4000
LITELLM_MASTER_KEY=sk-master-rag-proxy-token-2026

# Upstream LLM Provider API Keys (Managed by LiteLLM)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OLLAMA_API_BASE=http://ollama-service:11434 # Optional local model fallback

# Default Model Selection
MODEL_DEFAULT_EXTRACTOR=gpt-4o-mini
MODEL_DEFAULT_SUMMARIZER=gpt-4o-mini
MODEL_DEFAULT_REASONER=gpt-4o
MODEL_DEFAULT_EMBEDDING=text-embedding-3-large
MODEL_DEFAULT_RERANKER=rerank-v3.5

# ==============================================================================
# 3. VECTOR STORE (QDRANT)
# ==============================================================================
QDRANT_HOST=qdrant-service
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_URL=http://qdrant-service:6333
QDRANT_API_KEY=your-secure-qdrant-api-key   # Required if Qdrant authentication is enabled
QDRANT_USE_GRPC=true                       # Use gRPC for high-throughput vector upserts
QDRANT_CHUNK_COLLECTION=rag_chunks
QDRANT_SEMANTIC_COLLECTION=rag_semantic_layer
EMBEDDING_DIMENSION=1536

# ==============================================================================
# 4. KNOWLEDGE GRAPH (NEO4J)
# ==============================================================================
NEO4J_URI=bolt://neo4j-service:7687         # Use neo4j:// or neo4j+s:// for Aura / Cluster
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=StrongProductionPassword2026!
NEO4J_DATABASE=neo4j                       # Default database name
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT_SECS=30
NEO4J_GDS_ENABLED=true                     # Enables Graph Data Science (Leiden clustering)

# ==============================================================================
# 5. CACHE & MESSAGE BROKER (REDIS)
# ==============================================================================
REDIS_URL=redis://:RedisPassword2026!@redis-service:6379/0
REDIS_CACHE_DB=0
REDIS_CELERY_QUEUE_DB=1
REDIS_SEMANTIC_CACHE_TTL_SECS=86400        # 24 hours
SEMANTIC_CACHE_SIMILARITY_THRESHOLD=0.96

# ==============================================================================
# 6. RETRIEVAL BROKER SERVICE
# ==============================================================================
BROKER_HOST=0.0.0.0
BROKER_PORT=8000
BROKER_WORKERS=4
BROKER_TOKEN_BUDGET=3500
BROKER_RRF_K=60
BROKER_INTENT_CONFIDENCE_THRESHOLD=0.68
BROKER_FALLBACK_ENABLED=true
RERANKER_TYPE=cohere                       # cohere | local_cross_encoder | bge
LOCAL_RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# ==============================================================================
# 7. INGESTION WORKER (DOCLING + CELERY)
# ==============================================================================
INGESTION_WORKERS_CONCURRENCY=8
DOCLING_MAX_PAGE_BATCH=50
DOCLING_ENABLE_OCR=true
DOCLING_OCR_ENGINE=tesseract               # tesseract | easyocr
DOCLING_EXTRACT_TABLES=true

# Object Storage for Source Documents (S3 / GCS / Azure Blob)
STORAGE_BACKEND=s3                         # s3 | gcs | local
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=enterprise-rag-documents-vault

# ==============================================================================
# 8. OBSERVABILITY & TRACING (LANGFUSE / OPENTELEMETRY)
# ==============================================================================
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_HOST=http://langfuse-service:3000
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_TRACES_SAMPLER=always_on
```

---

## 3. Component-by-Component Configuration Details

### 3.1 LiteLLM Proxy Configuration (`litellm_config.yaml`)

LiteLLM acts as the model gateway. It handles model routing, fallbacks, rate limiting, and cost tracking.

**File Location:** `/etc/litellm/litellm_config.yaml`

```yaml
model_list:
  # Embedding Models
  - model_name: text-embedding-3-large
    litellm_params:
      model: openai/text-embedding-3-large
      api_key: "os.environ/OPENAI_API_KEY"

  # Fast Extractor & Summarizer (Level 1-2 Summaries & Intent Routing)
  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: "os.environ/OPENAI_API_KEY"
      timeout: 15
      max_retries: 3

  # High-Capability Reasoner (Complex Queries & Community Summaries)
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: "os.environ/OPENAI_API_KEY"
      timeout: 30

  # Anthropic Primary / Fallback Model
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: "os.environ/ANTHROPIC_API_KEY"

  # Cohere Reranker
  - model_name: rerank-v3.5
    litellm_params:
      model: cohere/rerank-v3.5
      api_key: "os.environ/COHERE_API_KEY"

router_settings:
  routing_strategy: "usage-based-routing"
  redis_url: "os.environ/REDIS_URL"
  enable_pre_call_checks: true

general_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"
  database_url: "os.environ/REDIS_URL"
  alerting: ["slack"]
```

---

### 3.2 Qdrant Vector Database Configuration

Qdrant hosts two collections: `rag_chunks` and `rag_semantic_layer`.

**Environment Variables for Qdrant Service:**
```bash
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
QDRANT__SERVICE__ENABLE_CORS=true
QDRANT__STORAGE__ON_DISK_PAYLOAD=true
QDRANT__SERVICE__API_KEY="your-secure-qdrant-api-key"
QDRANT__TELEMETRY_DISABLED=true
```

**Collection Initialization Script / Hook:**
Run once during bootstrap to provision collections and field indexes:

```bash
# 1. Create rag_chunks (Hybrid Dense + Sparse BM25)
curl -X PUT "http://localhost:6333/collections/rag_chunks" \
  -H "api-key: your-secure-qdrant-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "dense": { "size": 1536, "distance": "Cosine" }
    },
    "sparse_vectors": {
      "bm25": { "index": { "on_disk": false } }
    }
  }'

# 2. Create Payload Indexes for rag_chunks
for field in doc_id chunk_id entity_ids; do
  curl -X PUT "http://localhost:6333/collections/rag_chunks/index" \
    -H "api-key: your-secure-qdrant-api-key" \
    -H "Content-Type: application/json" \
    -d "{\"field_name\": \"$field\", \"field_schema\": \"keyword\"}"
done

# 3. Create rag_semantic_layer (Hierarchical RAPTOR Tree)
curl -X PUT "http://localhost:6333/collections/rag_semantic_layer" \
  -H "api-key: your-secure-qdrant-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": { "size": 1536, "distance": "Cosine" }
  }'

# 4. Create Payload Indexes for rag_semantic_layer
curl -X PUT "http://localhost:6333/collections/rag_semantic_layer/index" \
  -H "api-key: your-secure-qdrant-api-key" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "level", "field_schema": "integer"}'

for field in doc_id parent_id children_node_ids leaf_chunk_ids; do
  curl -X PUT "http://localhost:6333/collections/rag_semantic_layer/index" \
    -H "api-key: your-secure-qdrant-api-key" \
    -H "Content-Type: application/json" \
    -d "{\"field_name\": \"$field\", \"field_schema\": \"keyword\"}"
done
```

---

### 3.3 Neo4j Graph Database Configuration

Neo4j requires APOC and the Graph Data Science (GDS) plugin enabled for Leiden community clustering.

**Environment Variables for Neo4j Container / Server (`neo4j.conf` mapping):**
```bash
NEO4J_AUTH=neo4j/StrongProductionPassword2026!
NEO4J_PLUGINS='["apoc", "graph-data-science"]'
NEO4J_dbms_security_procedures_unrestricted="apoc.*,gds.*"
NEO4J_dbms_security_procedures_allowlist="apoc.*,gds.*"

# Memory Configuration (Allocate based on available RAM)
NEO4J_server_memory_heap_initial__size=4G
NEO4J_server_memory_heap_max__size=8G
NEO4J_server_memory_pagecache_size=4G

# Connection Pools & Logging
NEO4J_dbms_connector_bolt_enabled=true
NEO4J_dbms_connector_bolt_listen__address=0.0.0.0:7687
```

**Connection String Examples:**
- **Standard Driver:** `bolt://neo4j:StrongProductionPassword2026!@neo4j-service:7687`
- **Neo4j Aura / TLS Cluster:** `neo4j+s://<instance-id>.databases.neo4j.io`

---

### 3.4 Redis Configuration (Cache & Celery Broker)

Redis is partitioned across database indices to avoid cache and message collision:
- `DB 0`: Semantic Query Cache & LLM Extraction Cache
- `DB 1`: Celery Task Queue Broker & Result Backend

**Environment Variables:**
```bash
REDIS_URL=redis://:RedisPassword2026!@redis-service:6379/0
CELERY_BROKER_URL=redis://:RedisPassword2026!@redis-service:6379/1
CELERY_RESULT_BACKEND=redis://:RedisPassword2026!@redis-service:6379/1
```

**Redis Production Server Settings (`redis.conf`):**
```ini
requirepass RedisPassword2026!
maxmemory 4gb
maxmemory-policy volatile-lru
save 300 10
tcp-keepalive 300
```

---

### 3.5 Ingestion Worker Service (Celery + Docling)

The ingestion worker handles file download, Docling layout extraction, semantic chunking, and parallel store population.

**Execution Command:**
```bash
celery -A src.ingestion_worker worker --loglevel=INFO --concurrency=8 -Q ingestion_queue
```

**Configuration Properties:**
```python
CELERY_CONFIG = {
    "broker_url": os.getenv("CELERY_BROKER_URL"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND"),
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_track_started": True,
    "task_time_limit": 600,         # 10 minutes max per document
    "worker_prefetch_multiplier": 1, # Prevent memory exhaustion on large PDFs
}
```

---

### 3.6 Retrieval Broker Service (FastAPI)

The Broker coordinates the Intent Router, Qdrant search, Neo4j traversals, Weighted RRF, and Cross-Encoder Re-ranking.

**Execution Command:**
```bash
uvicorn src.broker_api:app --host 0.0.0.0 --port 8000 --workers 4
```

**Required Runtime Bindings:**
- `QDRANT_URL` and `QDRANT_API_KEY`
- `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`
- `LITELLM_BASE_URL` and `LITELLM_MASTER_KEY`
- `REDIS_URL`

---

### 3.7 Observability & Tracing (Langfuse & OpenTelemetry)

To trace query latencies, token consumption, and hallucination evaluations across all stores:

**Environment Variables for Broker and Workers:**
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANGFUSE_HOST=http://langfuse-service:3000
LANGFUSE_RELEASE=2026.10.1
```

**OpenTelemetry Exporter (Optional APM Integration):**
```bash
OTEL_SERVICE_NAME=rag-retrieval-broker
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

---

## 4. Docker Compose Orchestration Specification

Historical topology sketch only; this is not a tested or production-ready compose profile:

```yaml
version: '3.8'

services:
  # 1. Model Gateway
  litellm-proxy:
    image: ghcr.io/berriai/litellm:main-v1.45.0
    container_name: rag-litellm-proxy
    ports:
      - "4000:4000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - COHERE_API_KEY=${COHERE_API_KEY}
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./litellm_config.yaml:/etc/litellm/litellm_config.yaml
    command: ["--config", "/etc/litellm/litellm_config.yaml", "--port", "4000"]
    restart: unless-stopped

  # 2. Vector Database
  qdrant-service:
    image: qdrant/qdrant:v1.11.0
    container_name: rag-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped

  # 3. Graph Database
  neo4j-service:
    image: neo4j:5.23.0-enterprise # or 5.23.0-community
    container_name: rag-neo4j
    ports:
      - "7474:7474" # Browser UI
      - "7687:7687" # Bolt protocol
    environment:
      - NEO4J_AUTH=${NEO4J_USERNAME}/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*,gds.*
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

  # 4. Cache & Task Queue Broker
  redis-service:
    image: redis:7.2-alpine
    container_name: rag-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--requirepass", "RedisPassword2026!", "--maxmemory", "4gb", "--maxmemory-policy", "volatile-lru"]
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # 5. Retrieval Broker API
  retrieval-broker:
    build:
      context: .
      dockerfile: Dockerfile.broker
    container_name: rag-broker
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - qdrant-service
      - neo4j-service
      - redis-service
      - litellm-proxy
    restart: unless-stopped

volumes:
  qdrant_storage:
  neo4j_data:
  redis_data:
```

---

## 5. Deployment Verification Checklist

Execute these health checks after configuring and starting the services:

| Component | Health Check Target | Expected Response |
| :--- | :--- | :--- |
| **LiteLLM Proxy** | `curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:4000/health` | `{"healthy_endpoints": [...]}` |
| **Qdrant DB** | `curl http://localhost:6333/healthz` | `healthz check passed` |
| **Neo4j Bolt** | `cypher-shell -a bolt://localhost:7687 -u neo4j -p $NEO4J_PASSWORD "RETURN 1;"` | `1` |
| **Neo4j GDS** | `cypher-shell -a bolt://localhost:7687 -u neo4j -p $NEO4J_PASSWORD "RETURN gds.version();"` | Version string (e.g., `"2.6.x"`) |
| **Redis** | `redis-cli -a $REDIS_PASSWORD ping` | `PONG` |
| **Retrieval Broker** | `curl http://localhost:8000/health` | `{"status": "healthy", "stores": {"qdrant": true, "neo4j": true}}` |
