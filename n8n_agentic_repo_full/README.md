# n8n Agentic Pipeline (Production-ready scaffold)

This repository is a scaffold for running a production-capable n8n stack that supports:
- Agentic workflows (RAG + agent decisioning)
- Modular LLM integration (local Ollama endpoint + OpenAI)
- Vector DB (Weaviate) for retrieval
- Queue mode with workers (Postgres + Redis)
- Traefik reverse proxy with Let's Encrypt
- Gmail integration (via n8n credentials)

## What is included
- docker-compose.yml (Traefik, Postgres, Redis, Weaviate, Ollama placeholder, n8n main + worker)
- .env.example
- README
- prompts/ (system + verification prompts)
- workflows/agentic_rag_workflow.json (importable n8n workflow)
- infra/ (Hostinger and AWS EC2 setup guides)
- scripts/ (weaviate ingestion + FAISS microservice scaffold)
- terraform/ (basic Terraform file to provision an EC2 instance - example only)

## Quick start (Hostinger / EC2)
1. Copy `.env.example` to `.env` and edit values.
2. Create `secrets/` files:
   - `secrets/postgres_password.txt`
   - `secrets/openai_api_key.txt` (if using OpenAI)
3. Start stack:
   ```bash
   docker compose up -d
   ```
4. Open `https://<N8N_HOST>` once Traefik obtains TLS certs.
5. Import `workflows/agentic_rag_workflow.json` into n8n (Workflows -> Import).
6. Create Gmail credentials in n8n UI and test sending.

## Next steps / hardening
- Use AWS RDS and ElastiCache for Postgres/Redis in production.
- Move secrets to AWS Secrets Manager or HashiCorp Vault.
- Use MinIO or S3 for attachments (queue mode).
- Add Prometheus / Grafana for monitoring.

