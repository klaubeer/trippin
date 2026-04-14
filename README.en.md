<div align="center">

# ✈️ Trippin'

**AI-powered travel planning**

Enter your destination and dates. Four specialized AI agents work in sequence and deliver three complete itineraries — budget, comfort, and premium — with flights, accommodation, daily activities, an interactive map, and a downloadable PDF.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

[🇧🇷 Português](README.md) · [🇺🇸 English](#-trippin)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [API](#-api)
- [Monitoring](#-monitoring)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌍 Overview

Trippin' is a full-stack platform that demonstrates the use of **multiple AI agents** for automating complex, multi-step tasks. The user provides origin, destination, dates, and number of travelers. Four specialized agents — orchestrated via CrewAI — process the request in the background and deliver three complete itineraries with cost estimates.

**Average cost per generation:** ~$0.006 USD · **Average time:** ~70 seconds

---

## ✨ Features

| Feature | Description |
|---|---|
| **3 simultaneous itineraries** | Budget, Comfort, and Premium with distinct experiences and prices |
| **Real-time progress** | Server-Sent Events (SSE) show which agent is currently running |
| **Interactive map** | Geo-referenced activities on OpenStreetMap via Leaflet |
| **PDF download** | Full itinerary exportable as PDF (authenticated users) |
| **Sharing link** | Unique public URL per itinerary, no login required |
| **Monitoring dashboard** | Tokens, USD cost, latency, and status per agent/trip |
| **City autocomplete** | 6,600+ airports indexed via `airportsdata` |
| **Anonymous access** | Generate and view itineraries without signing up |
| **Internationalization** | UI available in Portuguese (BR) and English |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER                              │
│  Next.js 16 (React 19 + Tailwind 4 + next-intl)            │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  /planejar  │  │  /roteiros   │  │    /historico     │  │
│  │  Plan Form  │  │  Itinerary   │  │    Monitoring     │  │
│  └──────┬──────┘  └──────────────┘  └───────────────────┘  │
│         │ SSE (progress) + REST (data)                      │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                   FastAPI (uvicorn async)                    │
│  /api/viagens  /api/locais  /api/monitoramento  /api/auth   │
└────────────┬───────────────────────┬────────────────────────┘
             │ enqueue task          │ subscribe channel
┌────────────▼──────────┐  ┌────────▼───────────────────────┐
│    Celery Worker      │  │      Redis                      │
│                       │  │  • Celery broker               │
│  gerar_roteiro()      │  │  • SSE pub/sub                 │
│  ┌─────────────────┐  │  └────────────────────────────────┘
│  │ 1. FlightAgent  │  │
│  │ 2. HotelAgent   │  │  ┌─────────────────────────────────┐
│  │ 3. ActivityAgt  │  │  │       PostgreSQL 16              │
│  │ 4. Architect    │──┼─►│  travel_requests                │
│  └─────────────────┘  │  │  itineraries · flights · hotels │
└───────────────────────┘  │  activities · execution_logs   │
                           └─────────────────────────────────┘
```

### Agent Pipeline

```
Request ──► [FlightAgent] ──► [HotelAgent] ──► [ActivityAgent] ──► [Architect]
             gpt-4o-mini      gpt-4o-mini       gpt-4.1-mini        gpt-4.1-mini
             Flights/tier     Hotels/tier        3 distinct tiers    Final synthesis
             (3 levels)       (3 levels)         eco/comfort/prem    + total cost
```

---

## 🛠️ Tech Stack

### Backend

| Layer | Technology | Version |
|---|---|---|
| HTTP Framework | FastAPI | 0.115 |
| ASGI Server | Uvicorn | 0.32 |
| ORM | SQLAlchemy (async) | 2.0 |
| Migrations | Alembic | 1.14 |
| PostgreSQL driver | asyncpg (async) / psycopg2 (sync) | — |
| Task queue | Celery | 5.4 |
| Broker / Cache | Redis | 7 |
| Authentication | fastapi-users + JWT | 13.0 |
| AI Agents | CrewAI | ≥0.80 |
| LLM Provider | OpenAI (gpt-4o-mini, gpt-4.1-mini) | — |
| Streaming | SSE (sse-starlette) | 2.1 |
| Rate limiting | slowapi | 0.1 |
| PDF | ReportLab | 4.2 |
| Airport data | airportsdata (6,600+ IATA) | — |
| HTTP client | httpx | 0.28 |

### Frontend

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 16.2 |
| UI | React | 19 |
| Language | TypeScript | 5 |
| Styling | Tailwind CSS | 4 |
| Animations | Framer Motion | 12 |
| Maps | Leaflet + react-leaflet | 1.9 / 5.0 |
| i18n | next-intl | 4.9 |

### Infrastructure

| Service | Image |
|---|---|
| Database | postgres:16-alpine |
| Cache / Broker | redis:7-alpine |
| Backend | python:3.12-slim |
| Frontend | node:22-alpine |

---

## 📦 Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20
- An [OpenAI](https://platform.openai.com/api-keys) API key

> **Optional APIs** for real data (the system works in demo mode without them):
> [Amadeus](https://developers.amadeus.com/) (real flights/hotels) ·
> [Google Places](https://developers.google.com/maps/documentation/places/web-service) (real coordinates)

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/trippin.git
cd trippin

# 2. Copy and configure the environment file
cp .env.example .env
# Edit .env and fill in at least OPENAI_API_KEY

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Open the app
open http://localhost:3001
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| API (FastAPI) | http://localhost:8002 |
| Swagger / Docs | http://localhost:8002/docs |
| ReDoc | http://localhost:8002/redoc |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in the variables:

```env
# ── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://trippin:trippin@postgres:5432/trippin

# ── Cache / Queue ─────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── JWT Auth ──────────────────────────────────────────────────────
JWT_SECRET=replace-with-a-strong-unique-secret
JWT_ALGORITMO=HS256
JWT_EXPIRACAO_MINUTOS=10080   # 7 days

# ── AI (required) ─────────────────────────────────────────────────
OPENAI_API_KEY=sk-...         # Used by all four agents

# ── External APIs (optional — demo mode works without them) ───────
AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=
GOOGLE_PLACES_API_KEY=

# ── Email / SMTP (optional) ───────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORTA=587
SMTP_USUARIO=you@gmail.com
SMTP_SENHA=your-app-password

# ── App ───────────────────────────────────────────────────────────
AMBIENTE=dev
MODO_DEMO=false               # true = mock data, no external API calls
CORS_ORIGENS=["http://localhost:3000","http://localhost:3001"]
```

### Demo Mode

When `MODO_DEMO=true`, agents generate plausible data via LLM without consuming external APIs (Amadeus, Google Places). Useful for development when you don't have all integrations configured.

---

## 💻 Usage

### 1. Planning a trip

Go to `/planejar`, fill in the form, and click **Generate Itineraries**. Each agent's progress is displayed in real time via SSE.

### 2. Viewing the itinerary

After generation (~70s), the app redirects to `/roteiros/{id}`. Three tabs switch between Budget, Comfort, and Premium. Each tab shows flights, accommodation, daily activities, and a pin map.

### 3. Sharing

The **Share** button copies the page URL. Anyone with the link can view the itinerary without logging in.

### 4. Exporting PDF

Authenticated users can download the itinerary as a PDF via the **Download PDF** button.

---

## 📁 Project Structure

```
trippin/
├── backend/
│   ├── agentes/              # 4 CrewAI agents (flights, hotels, activities, architect)
│   ├── autenticacao/         # JWT + fastapi-users
│   ├── banco/                # SQLAlchemy engine and session
│   ├── compartilhamento/     # Public sharing endpoint
│   ├── locais/               # Airport autocomplete (airportsdata)
│   ├── monitoramento/        # Structured logging + per-agent metrics
│   ├── pdf/                  # PDF generation with ReportLab
│   ├── tarefas/              # Celery task (agent orchestration)
│   ├── viagens/              # Trip CRUD + SSE progress streaming
│   ├── alembic/              # Database migrations
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Config via pydantic-settings
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── app/[locale]/     # Locale-based routes (pt-BR / en)
│       │   ├── page.tsx      # Landing page
│       │   ├── planejar/     # Form + SSE progress
│       │   ├── roteiros/     # Itinerary viewer
│       │   ├── historico/    # Monitoring dashboard
│       │   └── compartilhar/ # Public view
│       ├── components/       # AutocompleteLocal, ActivityMap, VideoBackground
│       ├── lib/              # api.ts (fetch wrapper), useSSE.ts
│       └── messages/         # Translations pt-BR.json + en.json
│
├── docs/
│   ├── PRD.md                # Product Requirements Document
│   └── SDD.md                # System Design Document
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔌 API

Interactive documentation available at `http://localhost:8002/docs` (Swagger UI) and `http://localhost:8002/redoc`.

### Key endpoints

```
POST   /api/viagens/                    Create travel request
GET    /api/viagens/                    List user's trips
GET    /api/viagens/{id}                Full detail with itineraries
GET    /api/viagens/{id}/stream         SSE: real-time progress
GET    /api/viagens/{id}/roteiros/{tier}/pdf  PDF download

GET    /api/compartilhar/{slug}         Public itinerary view

GET    /api/locais/?q={city}            City/airport autocomplete

GET    /api/monitoramento/historico     Execution metrics per trip

POST   /api/auth/register               Sign up
POST   /api/auth/login                  Login (JWT)
GET    /api/usuarios/me                 Authenticated user profile
```

---

## 📊 Monitoring

The `/historico` dashboard shows, for each generated trip:

- **Status** of each agent (completed / failed)
- **Input and output tokens** per agent
- **USD cost** individual and total
- **Duration** in seconds per agent and total
- **Model** used

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a branch: `git checkout -b feat/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push to the branch: `git push origin feat/my-feature`
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

<div align="center">

Built with ☕ and lots of AI · [🇧🇷 Leia em Português](README.md)

</div>
