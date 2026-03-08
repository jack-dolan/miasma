# Miasma

Miasma is a personal privacy-defense project built around one idea: if data brokers will not reliably remove your data, degrade the value of what they keep.

> Many brokers and aggregators offer opt-out forms, but those opt-outs are often partial, temporary, or operationally weak. If reliable deletion is unrealistic, the next-best defensive move is to poison the well: intentionally spread false profile signals so the commercial identity graph is less accurate and less useful.

This repo is a working full-stack system for that strategy, and a hands-on engineering project for building production-style software end to end.

## Why This Exists

People-search and broker ecosystems continuously collect, buy, and re-aggregate personal data. Even when an opt-out path exists, records can reappear through refresh cycles and downstream vendors.

Miasma treats that as an adversarial data-quality problem:
- remove what can be removed
- measure what cannot
- inject noise where removal fails

The goal is not perfect invisibility. The goal is to make your profile less precise, less stable, and less monetizable.

## What It Does Today

The current MVP centers on opt-out execution for a single broker flow (`fastpeoplesearch`) with campaign tracking in both API and UI.

You can:
1. Create an opt-out campaign for a target identity.
2. Scan for candidate records.
3. Execute removal attempts.
4. Track campaign and per-submission outcomes (`removed`, `failed`, `skipped`, etc.).

MVP scope, non-goals, and exit criteria are locked in [`docs/MVP.md`](docs/MVP.md).

## How It Works

At runtime, the system combines a React frontend, a FastAPI backend, PostgreSQL for campaign/submission state, Redis for caching/session support, and Selenium-driven automation for broker interaction.

A typical campaign flow:
1. The frontend creates a campaign via the API.
2. The backend runs broker lookup/scan logic and stores candidate summaries.
3. The campaign executor creates and processes submission records through site-specific handlers.
4. Status and error details are persisted and surfaced in the Campaigns UI.

Around that core flow, the project also uses SQLAlchemy + Alembic for data modeling/migrations, BeautifulSoup/Requests/Pandas for scraping and data workflows, Docker Compose for local orchestration, and GitHub Actions plus security tooling (including Snyk) for CI and hygiene. Deployment docs target AWS-style infrastructure patterns (ECS/RDS/ElastiCache).

Frontend delivery is built with React, Vite, Tailwind CSS, and React Query; backend services run on Python/FastAPI with SQLAlchemy; containerized runtime and local orchestration use Docker and Docker Compose.

## Quick Start

```bash
git clone https://github.com/jack-dolan/miasma.git
cd miasma
docker compose up -d
```

Backend local run:

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend local run:

```bash
cd frontend
npm ci
npm run dev
```

## Demo + Validation

Use the MVP script in [`docs/MVP.md`](docs/MVP.md) for an end-to-end demo.

Core backend validation command:

```bash
docker compose exec -T backend pytest \
  tests/test_campaign_executor_optout.py \
  tests/test_campaign_executor.py \
  tests/integration/test_campaign_api.py \
  tests/unit/test_optout_fastpeoplesearch.py -q
```

## Repository Layout

- `backend/`: FastAPI app, domain models, services, scrapers, tests
- `frontend/`: React app, pages/components, API client, tests
- `docs/`: API/deployment/security docs plus MVP definition
- `infrastructure/`: Terraform and deployment scripts

## Disclaimer

This project is for legitimate privacy-defense use. You are responsible for using it in ways that comply with applicable laws and platform terms.
