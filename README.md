# n9n_Arks



1. an **agentic pipeline** (autonomous AI agents + tool chaining / RAG style)
2. a **hosted pipeline** (production-ready, self-hosted n8n with queue/workers, Postgres, Redis + TLS / monitoring)



# Executive summary

* For **production** run n8n in **queue mode** with a persistent relational DB (Postgres is recommended) and Redis for the queue. Use worker instances to scale background jobs. This gives reliability, horizontal scale and better webhook handling. ([n8n Docs][1])
* For **agentic pipelines** use n8n’s **AI Agent** + existing nodes (HTTP, DB, file, etc.) and implement a RAG (retrieve → prompt → tool → verify) pattern so the agent can call tools, read vector DB results, and verify responses. n8n has an Agent integration and has published guides on Agentic RAG. ([n8n][2])

---

# Table of contents

1. Architecture overview (agentic / hosted)
2. Requirements & prerequisites
3. Production-ready n8n stack: components and env vars
4. Docker Compose example (self-hosted, queue mode, Postgres + Redis + worker)
5. Agentic pipeline design — patterns & a concrete workflow
6. Hosted pipeline options (n8n Cloud / platform-as-a-service)
7. Operational concerns: security, backups, scaling, monitoring
8. Example: end-to-end agentic + hosted deployment checklist
9. Next steps & references

---

# 1. Architecture overview

## Agentic pipeline (logical)

User input (web UI / webhook) → n8n webhook node → Preprocessor (convert to structured prompt) → **AI Agent node** (decides sub-actions) → Tool calls:

* Vector DB lookup / RAG
* External web search / crawlers
* Database reads/writes (Postgres)
* Third-party API calls (e.g., Gmail, Slack)
  Agent verifies result → Postprocess → Output (response via webhook / DB / email).

This keeps the decision-making (LLM) and execution (n8n nodes) separated and auditable.

## Hosted pipeline (infrastructure)

* **n8n main (UI + webhook processor)** fronted by reverse proxy (Traefik / Nginx) + TLS
* **Postgres** (persistent storage for workflows, credentials, executions)
* **Redis** (queue broker)
* **n8n worker(s)** (process queued jobs, heavy tasks)
* Optional: **vector DB** (Milvus, Weaviate, Pinecone) for RAG, mounted file storage for large files, monitoring stack (Prometheus + Grafana), logging (Loki/ELK) and backups.

High-availability: run multiple webhook processors + workers across nodes, central Postgres and HA Redis (Sentinel/Cluster) for failover. Community and docs recommend queue mode + workers for scaling. ([n8n Docs][1])

---

# 2. Requirements & prerequisites

## Software

* Docker & Docker Compose (or Kubernetes) on the host(s). (n8n docs include Docker and K8s guides). ([n8n Docs][3])
* Postgres (12+) managed or self-hosted (production strongly prefers Postgres vs SQLite). ([n8n Docs][4])
* Redis (for queue mode). ([n8n Docs][1])
* Reverse proxy (Traefik recommended for automatic Let's Encrypt) or load balancer for HTTPS.
* Optional: Vector DB (Pinecone, Milvus, Weaviate) or hosted vector provider for RAG.
* Node-level roles: `n8n` main, `n8n-worker`, `postgres`, `redis`, `traefik` (optional), monitoring stack.

## Accounts / API keys

* LLM provider API key(s) (OpenAI, Anthropic, local LLM endpoints, or n8n AI Agent connector credentials). n8n supports various LLM integrations and has an AI Agent integration. ([n8n][2])
* Credentials for services the agent will use (Google, Slack, GitHub, etc.) — stored in n8n credentials (and can be overridden with env vars or secrets).

## Hardware (baseline)

* Small pilot: 2 vCPU, 4 GB RAM (single instance) + managed Postgres.
* Production: multiple cores, 8–32+ GB RAM depending on concurrency and large LLM usage; DB on dedicated instance.

---

# 3. Production-ready n8n stack — components & key environment variables

### Core components

* **n8n main** (UI & webhook router)
* **n8n worker(s)** (for background/work heavy nodes)
* **Postgres** — for persistence. Set `DB_TYPE=postgresdb` and `DB_POSTGRESDB_*` variables as required. ([n8n Docs][4])
* **Redis** — required for queue mode. ([n8n Docs][1])

### Important environment variables (examples / must-set)

(derived from docs; use secrets or *_FILE variants in production) ([n8n Docs][5])

* `DB_TYPE=postgresdb`
* `DB_POSTGRESDB_HOST`
* `DB_POSTGRESDB_PORT=5432`
* `DB_POSTGRESDB_DATABASE` (e.g., n8n)
* `DB_POSTGRESDB_USER`
* `DB_POSTGRESDB_PASSWORD`
* `N8N_HOST` (domain or host)
* `N8N_PORT=5678`
* `WEBHOOK_TUNNEL_URL` (if using tunnels)
* `N8N_BASIC_AUTH_ACTIVE=true` / `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` (or use OAuth / SSO)
* `EXECUTIONS_DATA_PRUNE=true` and `EXECUTIONS_DATA_MAX_AGE` — to prevent unbounded DB growth. (important for production pruning). ([n8n Community][6])
* Queue related:

  * `EXECUTIONS_PROCESS=queue` (enable queue mode) — configure queue mode, then run worker containers. (See official queue mode docs.) ([n8n Docs][1])
* `VUE_APP_URL_BASE_API` (if front-end needs API base)
* AI/provider keys: `OPENAI_API_KEY` or n8n credential files (best to store as external secrets)

> Always prefer passing secrets via Docker secrets or Kubernetes Secrets; using `_FILE` env var options lets you point env to files for safer secrets.

---

# 4. Docker Compose (production example — queue mode, Postgres, Redis, Traefik)

Below is a compact Docker Compose example to get you started. Customize volumes, networks, domain, and secrets as needed. This is a starting template — additional production hardening (secrets, firewall, backups) is required.

```yaml
version: "3.8"
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.tlschallenge=true"
      - "--certificatesresolvers.le.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./letsencrypt:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro

  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=n8n
    volumes:
      - ./pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    restart: unless-stopped
    volumes:
      - ./redisdata:/data

  n8n:
    image: n8nio/n8n:latest
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=your.domain.com
      - N8N_PORT=5678
      - EXECUTIONS_PROCESS=queue
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASS}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=336
    volumes:
      - ./n8n:/home/node/.n8n
    depends_on:
      - postgres
      - redis
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.n8n.rule=Host(`your.domain.com`)"
      - "traefik.http.routers.n8n.entrypoints=websecure"
      - "traefik.http.routers.n8n.tls.certresolver=le"
    restart: unless-stopped

  n8n-worker:
    image: n8nio/n8n:latest
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - EXECUTIONS_PROCESS=queue
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
```

**Notes**

* Put sensitive values in a `.env` or Docker secrets; prefer `.env` only in development.
* Run multiple `n8n-worker` replicas to increase throughput; the main `n8n` handles webhooks and the UI. Use `docker compose up -d --scale n8n-worker=3` or orchestrate with Kubernetes for bigger deployments. ([n8n Docs][7])

---

# 5. Agentic pipeline design — patterns & a concrete n8n workflow

## Patterns to use

1. **RAG (Retrieve & Generate)**

   * Retrieve documents from vector DB → build context → call LLM to generate plan → LLM suggests tool calls. Use n8n nodes to perform retrieval and DB queries. (n8n Agentic RAG guide is available). ([n8n Blog][8])

2. **Tooling abstraction**

   * Build small subworkflows for each tool (search, email, scrape, DB) and call them from the main agent. This keeps auditable logs.

3. **Verification loop**

   * After the agent returns a result, run a verification step (e.g., secondary LLM check, or deterministic checks) before committing changes.

4. **Idempotency & retries**

   * Use execution metadata, dedupe keys, and DB transactions for side-effecting actions. Use retries for intermittent failures.

## Concrete workflow (high level)

1. **Trigger**: `Webhook` node receives JSON input `{user_query, session_id}`.
2. **Preprocess**: `Function` node normalizes query and checks session context in Postgres.
3. **Retrieval**: `HTTP` or custom node queries your vector DB (Weaviate/Pinecone/Milvus) and returns top-K context docs.
4. **Agent**: `AI Agent` node (or LLM node) receives prompt template:

   * System: “You are an automated agent. Use the tools: SEARCH(), DB_READ(), DB_WRITE(), HTTP_POST().”
   * User: include top-K retrieved docs + explicit instructions + safety constraints.
5. **Action Routing**: Based on agent output, n8n triggers sub-workflows:

   * `SEARCH` → HTTP node to a search API
   * `DB_READ` → Postgres node
   * `DB_WRITE` → Postgres node
6. **Verify**: Another LLM step or rule-based checker validates the proposed change.
7. **Commit**: If verified, write to DB or call external API; return result to the user.

### Example: Agentic RAG with n8n nodes

* Webhook → Vector DB retrieve (HTTP/SDK) → AI Agent node `decide_action` → Switch node to route to subflows → Worker nodes handle heavy ops → Verification LLM node → Final webhook reply.

n8n’s AI Agent integration and blog explain the pattern and provide examples. ([n8n][2])

---

# 6. Hosted pipeline options

## 1) n8n Cloud (managed)

* Pros: managed backups, scaling, security, SSO options. Good if you want less ops overhead. See "Choose your n8n" docs for plans. ([n8n Docs][9])
* Cons: cost, less control over custom infra and on-prem data residency.

## 2) PaaS (Render, Railway, Fly, Railway templates)

* Many tutorials exist to deploy n8n on Render or Railway (often with managed Postgres). Good middle ground for teams that want less infra ops. Example templates: Railway n8n with worker and external Postgres. ([Railway][10])

## 3) Self-hosted (recommended for full control)

* Use Docker Compose (small orgs) or Kubernetes for scale/HA. Consider managed Postgres (RDS, Cloud SQL) and a hosted vector DB if you rely on RAG.

---

# 7. Operational concerns (security, backups, scaling, monitoring)

## Security

* Use TLS (Traefik/Let’s Encrypt) and enable `N8N_BASIC_AUTH` or SSO. Protect the UI and webhooks.
* Store secrets in Docker secrets / Vault / Kubernetes Secrets (use `_FILE` env var options). ([n8n Docs][5])
* Limit credential scope for any third-party API the agent can call.
* Audit logs: enable n8n execution logging, store logs in central logging.

## Backups

* Postgres backups (logical pg_dump + WAL or managed snapshotting). Schedule daily exports and test restores.
* Back up `~/.n8n` if you store file attachments locally.

## Monitoring & alerts

* Enable n8n metrics (Prometheus endpoint), use Prometheus + Grafana to monitor:

  * worker queue length, execution errors, event loop lag, memory usage. Community dashboards exist. ([n8n Community][11])

## Pruning & data retention

* Use `EXECUTIONS_DATA_PRUNE=true` and `EXECUTIONS_DATA_MAX_AGE` to keep DB size under control. Monitor DB growth and prune/compact periodically. ([n8n Community][6])

## Scaling

* Use queue mode + multiple `n8n-worker` processes; add webhook processors behind load balancer for HA. Redis should be run in HA mode (Sentinel/Cluster) for production. ([n8n Docs][1])

---

# 8. Example: end-to-end checklist (deploy & run agentic pipeline)

1. **Provision infra**

   * Server(s) or K8s cluster
   * Managed Postgres or server with Postgres 12+
   * Redis (standalone for small, Sentinel/Cluster for prod)
   * Domain + DNS

2. **Provision secrets** (store in Vault / Kubernetes Secrets or Docker secrets)

3. **Deploy reverse proxy** (Traefik) and enable TLS

4. **Deploy docker-compose** (or helm chart) with `n8n` (main) + `n8n-worker` + `postgres` + `redis`

5. **Set env vars**:

   * `DB_TYPE=postgresdb`, `DB_POSTGRESDB_*`, `EXECUTIONS_PROCESS=queue`, `REDIS_HOST`, `N8N_BASIC_AUTH_*`, `EXECUTIONS_DATA_PRUNE=true`

6. **Test workflow**:

   * Create webhook → trigger with sample payload → ensure worker picks up job and returns expected result

7. **Agentic workflow**:

   * Add AI Agent credentials (LLM)
   * Wire vector DB (or HTTP retrieval)
   * Build and test RAG prompt templates
   * Add verification step

8. **Monitoring & backups**:

   * Configure Prometheus + Grafana; set up Postgres backups.

9. **Failover & HA**:

   * Add more webhook processors and workers; set up Redis Sentinel; ensure Postgres is HA or managed with failover.

---

# 9. References & further reading

* n8n Docker installation & Docker-Compose docs. ([n8n Docs][3])
* Database environment variables (Postgres configuration for n8n). ([n8n Docs][5])
* Queue mode & scaling guide (workers + Redis). ([n8n Docs][1])
* n8n Agent & Agentic RAG blog (practical guide to building autonomous AI workflows). ([n8n][2])
* Community & tutorials: Docker + Traefik + Postgres starter templates and user guides (examples & templates). ([GitHub][12])

---

# Final notes & next steps

  • produce a **ready-to-run repo** (docker-compose + `.env.example` + README + sample workflows) tailored to your domain, or
  • build a concrete **agentic workflow** example that: webhook → RAG → agent decides → tool calls → verification, with exported n8n workflow JSON you can import.

Which would you like next? (repo + compose, or a concrete workflow JSON + prompt templates?)

[1]: https://docs.n8n.io/hosting/scaling/queue-mode/?utm_source=chatgpt.com "Configuring queue mode"
[2]: https://n8n.io/integrations/agent/?utm_source=chatgpt.com "AI Agent integrations | Workflow automation with n8n"
[3]: https://docs.n8n.io/hosting/installation/docker/?utm_source=chatgpt.com "Docker Installation"
[4]: https://docs.n8n.io/hosting/configuration/supported-databases-settings/?utm_source=chatgpt.com "Supported databases and settings"
[5]: https://docs.n8n.io/hosting/configuration/environment-variables/database/?utm_source=chatgpt.com "Database environment variables"
[6]: https://community.n8n.io/t/reducing-the-size-of-the-postgresql-dabase/29047?utm_source=chatgpt.com "Reducing the size of the PostgreSQL dabase - Questions"
[7]: https://docs.n8n.io/hosting/installation/server-setups/docker-compose/?utm_source=chatgpt.com "Docker Compose | n8n Docs"
[8]: https://blog.n8n.io/agentic-rag/?utm_source=chatgpt.com "Agentic RAG: A Guide to Building Autonomous AI Systems"
[9]: https://docs.n8n.io/choose-n8n/?utm_source=chatgpt.com "Choose your n8n"
[10]: https://railway.com/deploy/n8n-w-worker-externa?utm_source=chatgpt.com "Deploy n8n w/ worker, external pgsql"
[11]: https://community.n8n.io/t/ultimate-n8n-dev-container-with-debugging-monitoring-observability-dockers/121968?utm_source=chatgpt.com "Ultimate n8n Dev Container (with Debugging, Monitoring & ..."
[12]: https://github.com/brunosergi/self-hosted-n8n-template?utm_source=chatgpt.com "brunosergi/self-hosted-n8n-template"
