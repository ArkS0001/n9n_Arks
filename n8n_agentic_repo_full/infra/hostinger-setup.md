# infra/hostinger-setup.md
Hostinger VPS quick guide:

1. Provision a VPS with Ubuntu 22.04 via hPanel, choose a plan with sufficient CPU/RAM.
2. SSH into the VPS, install Docker & Docker Compose.
3. Upload this repo (git clone or SFTP).
4. Create `secrets/` files and `.env`.
5. Start services with `docker compose up -d`.
6. Point your domain to the VPS IP in Hostinger DNS.
7. Use Traefik to manage TLS automatically (compose already includes Traefik).
8. For backups, set up a cron job to `pg_dump` and rsync volumes to remote storage.
