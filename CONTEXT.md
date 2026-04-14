# CONTEXT.md — Trippin'

## STATUS GERAL DO PROJETO

- **Fase atual:** DESENVOLVIMENTO
- **Milestone atual:** Pipeline de geração funcionando end-to-end com OpenAI; histórico de execuções implementado
- **Última decisão relevante:** Migração de todos os agentes para OpenAI (4o-mini + 4.1-mini) — free tiers de Groq/Gemini/Anthropic tinham limites TPM muito restritivos para uso prático
- **Próximo passo:** Polimento de UI — login/registro, header de navegação, página de roteiros completa

---

## FEATURES

| Status | Feature | Observações |
|--------|---------|-------------|
| ✅ DONE | Infraestrutura Docker Compose | postgres, redis, backend, celery, frontend; volumes de logs |
| ✅ DONE | FastAPI + SQLAlchemy async + Alembic | config, banco, sessão |
| ✅ DONE | Autenticação (fastapi-users + JWT) | registro, login; SSE usa `usuario_atual_via_query` (query param) |
| ✅ DONE | Acesso anônimo | UUID_ANONIMO seeded no startup; geração sem login funciona |
| ✅ DONE | Modelos de viagem | SolicitacaoViagem, Roteiro, Voo, Hospedagem, Atividade |
| ✅ DONE | Monitoramento / Logging | LogExecucaoAgente (DB) + RotatingFileHandler; ContextoExecucao por agente |
| ✅ DONE | Tokens reais da API | `crew.usage_metrics` retorna prompt_tokens + completion_tokens reais (não heurística) |
| ✅ DONE | Endpoints REST | POST/GET viagens, SSE stream, PDF download, compartilhamento público |
| ✅ DONE | Endpoint histórico | GET /api/monitoramento/historico — todas as execuções com métricas agregadas |
| ✅ DONE | Celery task gerar_roteiro | orquestra 4 agentes CrewAI com logging |
| ✅ DONE | Agente Voos — GPT-4o-mini | fallback LLM credível sem Amadeus |
| ✅ DONE | Agente Hotéis — GPT-4o-mini | fallback LLM credível sem Amadeus |
| ✅ DONE | Agente Atividades — GPT-4.1-mini | fallback LLM credível sem Google Places |
| ✅ DONE | Arquiteto Roteiros — GPT-4.1-mini | sintetiza 3 roteiros, custo total |
| ✅ DONE | Autocomplete de cidades | componente AutocompleteLocal com lista estática (50+ cidades) + Amadeus fallback |
| ✅ DONE | Página /planejar dark redesign | bg-gradient azul/zinc, inputs translúcidos, acesso anônimo |
| ✅ DONE | Frontend: landing, formulário, SSE progresso, roteiros | Framer Motion, validação |
| ✅ DONE | Página /historico | monitoramento de tokens, custo, latência por agente e por roteiro |
| ✅ DONE | PDF (reportlab) + Mapa Leaflet + Compartilhamento público | — |
| 📋 PLANNED | Login/registro pages | tela de auth ainda não implementada no frontend |
| 📋 PLANNED | Header de navegação | links entre páginas |
| 📋 PLANNED | Seed usuário demo | demo@trippin.com / demo123 + roteiros pré-gerados |
| 📋 PLANNED | Deploy VPS | docker compose produção |

---

## MODELOS IA (DECISÃO ATIVA — 2026-04-13)

Todos os agentes migrados para OpenAI após problemas com free tiers:
- **Groq free tier:** 6000 TPM/min — insuficiente mesmo para uma requisição (agente usava 5000+ tokens por chamada)
- **Gemini free tier:** TPM muito baixo na prática (retryDelay de 53s)

| Agente | Modelo | Custo por requisição (aprox.) |
|--------|--------|-------------------------------|
| Voos | openai/gpt-4o-mini | ~$0.0006 |
| Hotéis | openai/gpt-4o-mini | ~$0.0005 |
| Atividades | openai/gpt-4.1-mini | ~$0.0026 |
| Arquiteto | openai/gpt-4.1-mini | ~$0.0025 |
| **Total por roteiro** | — | **~$0.006 (~R$0.03)** |

---

## DECISÕES ATIVAS — NÃO ALTERAR SEM DISCUSSÃO

- **Backend:** FastAPI + SQLAlchemy 2.0 async + Alembic
- **Auth:** fastapi-users + JWT; SSE autenticação via query param `?token=`; acesso anônimo via UUID_ANONIMO
- **Todos os agentes:** OpenAI (gpt-4o-mini para tarefas estruturadas, gpt-4.1-mini para criativas)
- **Origem:** Fixada em São Paulo / GRU
- **Modo sem APIs externas:** LLMs geram dados críveis; MODO_DEMO=false nas API keys preenchidas
- **Mapa:** Leaflet + OpenStreetMap (sem Google Maps, sem billing)
- **i18n:** next-intl com `routing.ts` e `navegacao.ts`
- **Nomenclatura:** PTBR em arquivos, pastas, variáveis, funções e classes

---

## PARA RODAR LOCALMENTE

```bash
# 1. Subir os serviços (API keys no .env)
docker compose up -d

# 2. Rodar migrações (primeira vez)
docker compose exec backend alembic upgrade head

# 3. Acessar
# Frontend: http://localhost:3001
# API docs: http://localhost:8002/docs
# Histórico: http://localhost:3001/pt-BR/historico
```

---

## CUSTO POR GERAÇÃO (medido em 2026-04-13)

Rota GRU→CDG (Paris), 7 dias, 2 viajantes:
- Total tokens: 10.628 (7.436 input + 3.192 output)
- Custo: $0.006227 USD (~R$ 0,03)
- Tempo total: ~48 segundos
