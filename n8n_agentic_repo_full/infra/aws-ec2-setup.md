# infra/aws-ec2-setup.md
This document outlines a simple EC2-based deployment for dev / small production.

1. Create an EC2 instance (Ubuntu 22.04) with at least 4 vCPU, 8GB RAM for small loads.
2. Open security group ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 5678 (optional).
3. SSH into the instance and install Docker & Docker Compose:
   https://docs.docker.com/engine/install/ubuntu/
4. Clone this repo, create `secrets/` files and `.env` from `.env.example`.
5. Run `docker compose up -d`.
6. For production scale consider:
   - RDS for Postgres
   - ElastiCache for Redis
   - Put Traefik behind an ALB or use Route53 + Elastic IP
   - Use AWS Secrets Manager for secrets and S3 for backups.
