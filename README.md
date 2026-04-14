<div align="center">

# ✈️ Trippin'

**Planejamento de viagens com inteligência artificial**

Informe o destino e as datas. Quatro agentes de IA trabalham em paralelo e entregam três roteiros completos — econômico, conforto e premium — com voos, hospedagem, atividades diárias, mapa interativo e PDF para download.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

[🇧🇷 Português](#-trippin) · [🇺🇸 English](README.en.md)

</div>

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Stack Tecnológica](#-stack-tecnológica)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API](#-api)
- [Monitoramento](#-monitoramento)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

---

## 🌍 Visão Geral

O Trippin' é uma plataforma full-stack que demonstra o uso de **múltiplos agentes de IA** para automação de tarefas complexas. O usuário informa origem, destino, datas e número de viajantes. Quatro agentes especializados — orquestrados via CrewAI — processam a solicitação em background e entregam três roteiros completos com custo estimado.

**Custo médio por geração:** ~$0,006 USD · **Tempo médio:** ~70 segundos

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **3 roteiros simultâneos** | Econômico, Conforto e Premium com experiências e preços distintos |
| **Progresso em tempo real** | Server-Sent Events (SSE) mostram qual agente está executando |
| **Mapa interativo** | Atividades georreferenciadas no OpenStreetMap via Leaflet |
| **PDF para download** | Roteiro completo exportável em PDF (usuários autenticados) |
| **Link de compartilhamento** | URL pública única por roteiro, sem login necessário |
| **Dashboard de monitoramento** | Tokens, custo USD, latência e status por agente/viagem |
| **Autocomplete de cidades** | 6.600+ aeroportos indexados via `airportsdata` |
| **Acesso anônimo** | Geração e visualização de roteiros sem cadastro |
| **Internacionalização** | Interface em Português (BR) e Inglês |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER                              │
│  Next.js 16 (React 19 + Tailwind 4 + next-intl)            │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  /planejar  │  │  /roteiros   │  │    /historico     │  │
│  │  Formulário │  │  Visualização│  │  Monitoramento    │  │
│  └──────┬──────┘  └──────────────┘  └───────────────────┘  │
│         │ SSE (progresso) + REST (dados)                    │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                   FastAPI (uvicorn async)                    │
│  /api/viagens  /api/locais  /api/monitoramento  /api/auth   │
└────────────┬───────────────────────┬────────────────────────┘
             │ enfileira task        │ assina canal
┌────────────▼──────────┐  ┌────────▼───────────────────────┐
│    Celery Worker      │  │      Redis                      │
│                       │  │  • Broker Celery               │
│  gerar_roteiro()      │  │  • Pub/Sub SSE                 │
│  ┌─────────────────┐  │  └────────────────────────────────┘
│  │ 1. AgenteVoos   │  │
│  │ 2. AgenteHoteis │  │  ┌─────────────────────────────────┐
│  │ 3. AgenteAtiv.  │  │  │       PostgreSQL 16              │
│  │ 4. Arquiteto    │──┼─►│  solicitacoes_viagem             │
│  └─────────────────┘  │  │  roteiros · voos · hospedagens  │
└───────────────────────┘  │  atividades · logs_execucao     │
                           └─────────────────────────────────┘
```

### Pipeline de Agentes

```
Solicitação ──► [AgenteVoos] ──► [AgenteHoteis] ──► [AgenteAtividades] ──► [Arquiteto]
                gpt-4o-mini      gpt-4o-mini         gpt-4.1-mini          gpt-4.1-mini
                Voos por tier    Hotéis por tier      3 tiers distintos     Síntese final
                (3 níveis)       (3 níveis)           eco/conf/premium      + custo total
```

---

## 🛠️ Stack Tecnológica

### Backend

| Camada | Tecnologia | Versão |
|---|---|---|
| Framework HTTP | FastAPI | 0.115 |
| Servidor ASGI | Uvicorn | 0.32 |
| ORM | SQLAlchemy (async) | 2.0 |
| Migrations | Alembic | 1.14 |
| Driver PostgreSQL | asyncpg (async) / psycopg2 (sync) | — |
| Fila de tarefas | Celery | 5.4 |
| Broker / Cache | Redis | 7 |
| Autenticação | fastapi-users + JWT | 13.0 |
| Agentes de IA | CrewAI | ≥0.80 |
| Provider LLM | OpenAI (gpt-4o-mini, gpt-4.1-mini) | — |
| Streaming | SSE (sse-starlette) | 2.1 |
| Rate limiting | slowapi | 0.1 |
| PDF | ReportLab | 4.2 |
| Dados aeroportos | airportsdata (6.600+ IATA) | — |
| HTTP client | httpx | 0.28 |

### Frontend

| Camada | Tecnologia | Versão |
|---|---|---|
| Framework | Next.js (App Router) | 16.2 |
| UI | React | 19 |
| Linguagem | TypeScript | 5 |
| Estilização | Tailwind CSS | 4 |
| Animações | Framer Motion | 12 |
| Mapas | Leaflet + react-leaflet | 1.9 / 5.0 |
| i18n | next-intl | 4.9 |

### Infraestrutura

| Serviço | Imagem |
|---|---|
| Banco de dados | postgres:16-alpine |
| Cache / Broker | redis:7-alpine |
| Backend | python:3.12-slim |
| Frontend | node:22-alpine |

---

> **APIs opcionais** para dados reais (o sistema opera em modo demo sem elas):
> [Amadeus](https://developers.amadeus.com/) (voos/hotéis reais) ·
> [Google Places](https://developers.google.com/maps/documentation/places/web-service) (coordenadas reais)


### Modo Demo

Se `MODO_DEMO=true`, os agentes geram dados plausíveis via LLM sem consumir as APIs externas (Amadeus, Google Places). Útil para desenvolvimento sem configurar todas as integrações.

---

## 💻 Uso

### 1. Planejando uma viagem

Acesse `/planejar`, preencha o formulário e clique em **Gerar Roteiros**. O progresso de cada agente é exibido em tempo real via SSE.

### 2. Visualizando o roteiro

Após a geração (~70s), o app redireciona para `/roteiros/{id}`. Três abas alternam entre Econômico, Conforto e Premium. Cada aba mostra voos, hospedagem, atividades dia a dia e um mapa com pins.

### 3. Compartilhando

O botão **Compartilhar** copia a URL da página. Qualquer pessoa com o link pode visualizar o roteiro sem login.

### 4. Exportando PDF

Usuários autenticados podem baixar o roteiro em PDF via o botão **Baixar PDF**.

---

## 📊 Monitoramento

O dashboard em `/historico` exibe, para cada viagem gerada:

- **Status** de cada agente (concluído / falhou)
- **Tokens** de entrada e saída por agente
- **Custo USD** individual e total
- **Duração** em segundos por agente e total
- **Modelo** utilizado

---

## 📄 Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais informações.

---

<div align="center">

Feito com ☕ e muita IA · [🇺🇸 Read in English](README.en.md)

</div>
