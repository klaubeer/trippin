"""
Configurações centralizadas da aplicação via pydantic-settings.

Por que pydantic-settings?
- Lê variáveis de ambiente e arquivo .env automaticamente
- Valida tipos (str, int, bool, list) sem código extra — se DATABASE_URL estiver ausente, falha na inicialização
- Um único objeto `configuracoes` importado em qualquer módulo, sem globals espalhados
- `extra="ignore"` garante que variáveis desconhecidas no .env não causam erro
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Banco de dados ────────────────────────────────────────────────────────
    # asyncpg é o driver async para PostgreSQL (necessário para SQLAlchemy async)
    database_url: str = "postgresql+asyncpg://trippin:trippin@localhost:5432/trippin"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    # Redis serve dupla função:
    # 1. Broker do Celery: fila de tarefas (POST /viagens/ → Celery task)
    # 2. Pub/Sub para SSE: o worker publica progresso, o FastAPI assina e transmite ao browser
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    # jwt_secret DEVE ser trocado em produção (gerar com: openssl rand -hex 32)
    # HS256 é simétrico — mesma chave para assinar e verificar. Suficiente para monolito.
    jwt_secret: str = "mude-este-secret-em-producao"
    jwt_algoritmo: str = "HS256"
    jwt_expiracao_minutos: int = 60 * 24 * 7  # 7 dias — evita logout frequente

    # ── E-mail ────────────────────────────────────────────────────────────────
    # Usado por fastapi-users para verificação de conta e reset de senha.
    # Em desenvolvimento, pode deixar vazio — os tokens são impressos no log do terminal.
    smtp_host: str = "smtp.gmail.com"
    smtp_porta: int = 587
    smtp_usuario: str = ""
    smtp_senha: str = ""
    email_remetente: str = "noreply@trippin.com"

    # ── Amadeus (voos e hotéis) ───────────────────────────────────────────────
    # Sandbox gratuito em test.api.amadeus.com — dados fictícios mas estrutura real.
    # Se vazio, os agentes geram dados plausíveis via LLM (modo fallback).
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_ambiente: str = "test"  # "test" (sandbox) | "production" (dados reais, pago)

    # ── Google Places ─────────────────────────────────────────────────────────
    # Usado pelo agente de atividades para buscar pontos turísticos com coordenadas reais.
    # Se vazio, o LLM gera atividades plausíveis com coordenadas aproximadas.
    google_places_api_key: str = ""

    # ── Provedores de IA ──────────────────────────────────────────────────────
    # Cada agente usa um LLM diferente — decisão intencional para demonstrar
    # versatilidade com múltiplos providers no portfólio.
    groq_api_key: str = ""          # Agente de Voos — Llama 3.1 8B (gratuito)
    google_ai_api_key: str = ""     # Agente de Hotéis — Gemini Flash 1.5 (tier gratuito)
    anthropic_api_key: str = ""     # Agente de Atividades — Claude Haiku (pago, barato)
    openai_api_key: str = ""        # Arquiteto de Roteiros — GPT-4o-mini (pago, barato)

    # ── App ───────────────────────────────────────────────────────────────────
    ambiente: str = "dev"  # "dev" (Swagger ativo) | "prod" (Swagger desabilitado)
    cors_origens: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    timeout_agentes_segundos: int = 300  # 5 minutos — cada agente pode demorar se o LLM estiver lento

    # ── Modo Demo ─────────────────────────────────────────────────────────────
    # Quando True, todos os agentes pulam as chamadas às APIs externas (Amadeus, Google Places)
    # e geram dados diretamente via LLM. Útil para rodar sem configurar API keys.
    modo_demo: bool = False


# Singleton importado pelos outros módulos: `from config import configuracoes`
configuracoes = Configuracoes()
