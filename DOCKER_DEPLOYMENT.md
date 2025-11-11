# Docker Deployment Guide

This guide covers deploying the Form 13F AI Agent using Docker containers.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Minimum 2GB RAM available
- Minimum 10GB disk space

## Quick Start (Development)

1. **Clone the repository and navigate to the project:**
   ```bash
   cd form13f_aiagent
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and set required variables:**
   ```bash
   # Required
   SEC_USER_AGENT="YourCompanyName contact@youremail.com"
   ANTHROPIC_API_KEY="sk-ant-your-key-here"
   DB_PASSWORD="your_secure_password"
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Check logs:**
   ```bash
   docker-compose logs -f api
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

## Production Deployment

1. **Set production environment variables in `.env`:**
   ```bash
   ENVIRONMENT=production
   LOG_LEVEL=warning
   DB_PASSWORD="strong_random_password_here"
   ```

2. **Start with production configuration:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Run database migrations:**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

## Container Management

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres
```

### Rebuild containers
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Restart a service
```bash
docker-compose restart api
```

## Database Management

### Access PostgreSQL shell
```bash
docker-compose exec postgres psql -U form13f_user -d form13f
```

### Run migrations
```bash
docker-compose exec api alembic upgrade head
```

### Create a new migration
```bash
docker-compose exec api alembic revision --autogenerate -m "description"
```

### Backup database
```bash
docker-compose exec postgres pg_dump -U form13f_user form13f > backup.sql
```

### Restore database
```bash
docker-compose exec -T postgres psql -U form13f_user form13f < backup.sql
```

## Scaling

### Scale API workers (production)
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale api=3
```

Note: You'll need a load balancer (nginx, traefik) to distribute traffic.

## Monitoring

### Health checks
```bash
# API health
curl http://localhost:8000/health

# PostgreSQL health
docker-compose exec postgres pg_isready -U form13f_user
```

### Resource usage
```bash
docker stats
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs api

# Check if port is already in use
netstat -an | grep 8000
```

### Database connection errors
```bash
# Verify PostgreSQL is healthy
docker-compose ps

# Check database connectivity
docker-compose exec api python -c "from sqlalchemy import create_engine; import os; engine = create_engine(os.getenv('DATABASE_URL')); print('Connected!' if engine.connect() else 'Failed')"
```

### Reset everything
```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d
```

## Security Best Practices

1. **Never commit `.env` file** - It contains secrets
2. **Use strong passwords** - Especially for `DB_PASSWORD`
3. **Run as non-root** - The Dockerfile already does this
4. **Limit resource usage** - Use docker-compose.prod.yml resource limits
5. **Regular updates** - Keep base images updated
6. **Network isolation** - Services communicate only via internal network

## Volume Management

### Data persistence
- `postgres_data`: PostgreSQL database files
- `./data`: Form 13F data files (raw, processed, cache)
- `./logs`: Application logs

### Backup volumes
```bash
docker run --rm -v form13f_postgres_data:/data -v $(pwd):/backup busybox tar czf /backup/postgres_backup.tar.gz /data
```

## Environment-specific Configurations

### Development
- Hot reload enabled (`--reload`)
- Verbose logging (`LOG_LEVEL=debug`)
- Single worker

### Production
- No reload
- 4 workers (`--workers 4`)
- Resource limits
- Warning-level logging
- Read-only data volumes

## Next Steps

1. Set up reverse proxy (nginx/traefik) for HTTPS
2. Configure log aggregation (ELK, Loki)
3. Set up monitoring (Prometheus, Grafana)
4. Implement CI/CD pipeline
5. Configure backup automation
