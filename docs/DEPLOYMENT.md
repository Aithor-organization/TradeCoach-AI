# TradeCoach-AI Deployment Guide

## Local Development
```bash
cd TradeCoach-AI
cp backend/.env.example backend/.env  # fill in keys
cp frontend/.env.example frontend/.env.local
docker compose up  # or run backend/frontend separately
```

## Staging (devnet)
```bash
# Set SOLANA_NETWORK=devnet in backend/.env
docker compose -f docker-compose.prod.yml up -d --build
curl https://staging.your-domain.com/health
```

## Production (mainnet-beta)
```bash
# 1. TLS: certbot certonly --standalone -d your-domain.com
# 2. Copy certs to nginx/ssl/
# 3. Set SOLANA_NETWORK=mainnet-beta, JWT_SECRET=$(openssl rand -hex 32)
# 4. Update nginx.conf server_name
docker compose -f docker-compose.prod.yml up -d --build
```

## Environment Variables
See `backend/.env.example` and `frontend/.env.example`

## Monitoring
- GET /health — server status
- Docker: `docker compose ps` / `docker stats`
- Nginx logs: `docker exec tradecoach-nginx tail -f /var/log/nginx/access.log`
