# Trading Bot

Automated stock-market analysis and paper-trading system for US stocks.
See [PLAN.md](PLAN.md) for the full development plan.

## Status

Phase 1 — Infrastructure (in progress).

## Quick Start

```text
cp .env.example .env
docker compose up -d
```

Check the API:

```text
curl http://localhost:8000/health
```

## Development

Run tests:

```text
pytest
```
