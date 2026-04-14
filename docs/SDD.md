# SDD — Trippin'
### Documento de Design de Software
**Versão:** 1.0 | **Data:** 2026-04-11 | **Status:** APROVADO

---

## 1. Decisões Arquiteturais (ADRs)

### ADR-01: FastAPI + Next.js App Router
| | |
|---|---|
| **Contexto** | Precisamos de um backend para API de IA/agentes e um frontend moderno |
| **Decisão** | FastAPI (backend) + Next.js 14 App Router (frontend) |
| **Motivo** | FastAPI é padrão no ecossistema Python/IA, async nativo facilita SSE. Next.js App Router demonstra domínio de RSC e rotas modernas |
| **Alternativa descartada** | Django + DRF — bom ORM e admin, mas async retrofitado, mais verboso para API-only |
| **Consequências** | Backend em `:8000`, frontend em `:3000`, comunicação via REST + SSE |

### ADR-02: Origem fixa em São Paulo (GRU)
| | |
|---|---|
| **Decisão** | Hardcode origem = GRU em todos os agentes |
| **Motivo** | Simplifica UX e reduz complexidade sem perder o efeito do portfólio |
| **Consequência** | Mencionar na UI: "Partindo de São Paulo (GRU)" |

### ADR-03: Múltiplos AI providers por agente
| | |
|---|---|
| **Decisão** | Cada agente usa um provider diferente para demonstrar versatilidade |
| **Motivo** | Portfólio: mostrar domínio de múltiplos ecossistemas de IA |
| **Consequência** | 4 API keys distintas no `.env` |

| Agente | Provider | Modelo | Custo |
|--------|----------|--------|-------|
| Agente de Voos | Groq | Llama 3.1 8B | Grátis |
| Agente de Hotéis | Google | Gemini Flash 1.5 | Tier grátis |
| Agente de Atividades | Anthropic | Claude Haiku | Muito barato |
| Arquiteto de Roteiros | OpenAI | GPT-4o-mini | Muito barato |

### ADR-04: SSE para streaming de progresso
| | |
|---|---|
| **Decisão** | Server-Sent Events via `sse-starlette` |
| **Motivo** | Unidirecional (servidor → cliente), nativo em FastAPI async, mais simples que WebSocket |
| **Alternativa descartada** | WebSocket — overhead desnecessário para comunicação unidirecional |

### ADR-05: Leaflet + OpenStreetMap para mapa
| | |
|---|---|
| **Decisão** | React-Leaflet com tiles OpenStreetMap |
| **Motivo** | 100% gratuito, sem billing, sem API key |
| **Alternativa descartada** | Google Maps — requer billing mesmo no tier grátis |

### ADR-06: next-intl para i18n
| | |
|---|---|
| **Decisão** | `next-intl` com `messages/en.json` e `messages/pt-BR.json` |
| **Motivo** | Integração nativa com App Router, sem config extra |

### ADR-07: SQLAlchemy 2.0 async + Alembic
| | |
|---|---|
| **Decisão** | ORM async com SQLAlchemy 2.0 + Alembic para migrações |
| **Motivo** | Compatível com FastAPI async, padrão da indústria para Python não-Django |
| **Consequência** | Mais verboso que Django ORM, mas mais explícito e flexível |

### ADR-08: fastapi-users para autenticação
| | |
|---|---|
| **Decisão** | `fastapi-users` com JWT + verificação de e-mail |
| **Motivo** | Solução completa de auth para FastAPI, evita reimplementar |
| **Alternativa descartada** | Auth manual — desnecessário para portfólio |

---

## 2. Estrutura de Pastas

```
trippin/
├── docs/
│   ├── PRD.md
│   └── SDD.md
├── backend/
│   ├── main.py                      # App FastAPI, routers, lifespan
│   ├── config.py                    # Settings via pydantic-settings
│   ├── banco/
│   │   ├── __init__.py
│   │   ├── sessao.py                # AsyncSession + engine
│   │   └── base.py                  # Base declarativa SQLAlchemy
│   ├── autenticacao/
│   │   ├── __init__.py
│   │   ├── modelos.py               # Usuario (extends fastapi-users base)
│   │   ├── esquemas.py              # Pydantic schemas de auth
│   │   └── roteador.py              # Endpoints auth
│   ├── viagens/
│   │   ├── __init__.py
│   │   ├── modelos.py               # SolicitacaoViagem, Roteiro, Voo, Hospedagem, Atividade
│   │   ├── esquemas.py              # Pydantic schemas
│   │   └── roteador.py              # Endpoints /api/viagens/
│   ├── agentes/
│   │   ├── __init__.py
│   │   ├── agente_voos.py           # Groq + Amadeus
│   │   ├── agente_hoteis.py         # Gemini + Amadeus
│   │   ├── agente_atividades.py     # Claude Haiku + Google Places
│   │   └── arquiteto_roteiros.py    # GPT-4o-mini — síntese final
│   ├── tarefas/
│   │   ├── __init__.py
│   │   ├── worker.py                # Celery app instance
│   │   └── gerar_roteiro.py         # Task principal
│   ├── compartilhamento/
│   │   ├── __init__.py
│   │   └── roteador.py              # GET /api/compartilhar/{slug}
│   └── pdf/
│       ├── __init__.py
│       └── gerador.py               # reportlab PDF generation
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── [locale]/
│   │   │       ├── layout.tsx
│   │   │       ├── page.tsx              # Landing
│   │   │       ├── planejar/
│   │   │       │   └── page.tsx          # Form + SSE progress
│   │   │       ├── roteiros/
│   │   │       │   └── [id]/
│   │   │       │       └── page.tsx      # Roteiro detail + mapa
│   │   │       ├── minhas-viagens/
│   │   │       │   └── page.tsx          # Histórico
│   │   │       └── compartilhar/
│   │   │           └── [slug]/
│   │   │               └── page.tsx      # Página pública de roteiro
│   │   ├── components/
│   │   │   ├── ui/                       # Componentes base (botão, input, etc.)
│   │   │   ├── mapa/                     # React-Leaflet wrapper
│   │   │   └── roteiro/                  # Cards de voo, hotel, atividade
│   │   ├── lib/
│   │   │   ├── api.ts                    # Fetch wrapper tipado
│   │   │   └── useSSE.ts                 # Hook SSE reutilizável
│   │   └── messages/
│   │       ├── en.json
│   │       └── pt-BR.json
│   ├── middleware.ts                     # next-intl locale detection
│   └── i18n.ts
├── alembic/
│   ├── env.py
│   └── versions/
├── docker-compose.yml
├── CONTEXT.md
└── .env.example
```

---

## 3. Modelos de Dados

```python
# autenticacao/modelos.py
class Usuario(SQLAlchemyBaseUserTableUUID):
    nome: Mapped[str]

# viagens/modelos.py
class SolicitacaoViagem(Base):
    id: UUID (PK)
    usuario_id: FK → Usuario
    destino: str
    iata_destino: str
    data_inicio: date
    data_fim: date
    num_viajantes: int
    status: Enum("pendente", "processando", "concluido", "falhou")
    slug: UUID  # compartilhamento público
    criado_em: datetime

class Roteiro(Base):
    id: UUID (PK)
    solicitacao_id: FK → SolicitacaoViagem
    nivel: Enum("economico", "conforto", "premium")
    custo_total_estimado: Decimal
    resumo: str
    criado_em: datetime

class Voo(Base):
    id: UUID (PK)
    roteiro_id: FK → Roteiro
    companhia: str
    partida: datetime
    chegada: datetime
    preco: Decimal
    link_reserva: str

class Hospedagem(Base):
    id: UUID (PK)
    roteiro_id: FK → Roteiro
    nome: str
    tipo: str
    preco_por_noite: Decimal
    avaliacao: float
    link_reserva: str

class Atividade(Base):
    id: UUID (PK)
    roteiro_id: FK → Roteiro
    nome: str
    dia: int
    horario: time
    descricao: str
    custo_estimado: Decimal
    latitude: float
    longitude: float
```

---

## 4. Endpoints da API

```
# Autenticação (fastapi-users)
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

# Viagens
POST   /api/viagens/                       # Cria SolicitacaoViagem + dispara Celery
GET    /api/viagens/                       # Lista viagens do usuário autenticado
GET    /api/viagens/{id}
GET    /api/viagens/{id}/stream            # SSE — progresso dos agentes
GET    /api/viagens/{id}/roteiros          # Retorna os 3 roteiros

# Compartilhamento
GET    /api/compartilhar/{slug}            # Público, sem auth

# PDF
GET    /api/viagens/{id}/roteiros/{nivel}/pdf
```

---

## 5. Fluxo de Geração de Roteiro

```
[Frontend] POST /api/viagens/
    → [Backend] Cria SolicitacaoViagem (status=pendente)
    → [Backend] Dispara Celery task gerar_roteiro.delay(solicitacao_id)
    → [Backend] Retorna {id, status}

[Frontend] GET /api/viagens/{id}/stream  (SSE)
    ← evento: {agente: "voos", status: "iniciando"}
    ← evento: {agente: "voos", status: "concluido", dados: {...}}
    ← evento: {agente: "hoteis", status: "iniciando"}
    ← evento: {agente: "hoteis", status: "concluido", dados: {...}}
    ← evento: {agente: "atividades", status: "iniciando"}
    ← evento: {agente: "atividades", status: "concluido", dados: {...}}
    ← evento: {agente: "arquiteto", status: "iniciando"}
    ← evento: {agente: "arquiteto", status: "concluido"}
    ← evento: {tipo: "finalizado", solicitacao_id: "..."}

[Celery Task] gerar_roteiro(solicitacao_id)
    → AgentesVoos.pesquisar() [Groq + Amadeus]
    → AgenteHoteis.pesquisar() [Gemini + Amadeus]
    → AgenteAtividades.pesquisar() [Haiku + Google Places]
    → ArquitetoRoteiros.montar(voos, hoteis, atividades) [GPT-4o-mini]
    → Salva Roteiro(economico), Roteiro(conforto), Roteiro(premium) no banco
    → Atualiza SolicitacaoViagem.status = "concluido"
    → Publica evento SSE: finalizado
```

---

## 6. Considerações de Segurança

| Superfície | Medida |
|-----------|--------|
| Endpoints autenticados | JWT obrigatório via fastapi-users |
| Rate limiting | slowapi: 5 req/hora por usuário em POST /api/viagens/ |
| Validação de entrada | Pydantic v2 em todos os schemas |
| Compartilhamento | Slug UUID v4 — impossível de adivinhar |
| Secrets | Somente via variáveis de ambiente — nunca hardcoded |
| CORS | Whitelist explícita no FastAPI |
