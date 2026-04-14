"""
Ponto de entrada da aplicação FastAPI.

Por que FastAPI?
- Framework assíncrono nativo (async/await), essencial para SSE e chamadas paralelas às APIs externas
- Geração automática de documentação Swagger em /docs (útil durante desenvolvimento)
- Validação de request/response via Pydantic sem código extra
- Performance comparável a Node.js/Go para I/O-bound workloads

Por que não Django REST Framework?
- Django tem ORM e admin excelentes, mas async é retrofitado (ASGI adicionado depois)
- Para uma API pura sem necessidade de admin, FastAPI é mais leve e direto
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import configuracoes


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    No startup: garante que o usuário anônimo existe no banco.
    """
    await _garantir_usuario_anonimo()
    yield


async def _garantir_usuario_anonimo():
    """
    Cria o usuário anônimo (UUID zerado) se ainda não existir.
    Usado como usuario_id para solicitações sem autenticação.
    """
    import uuid
    from banco.sessao import fabrica_sessao
    from autenticacao.modelos import Usuario
    from autenticacao.gerenciador import UUID_ANONIMO
    from sqlalchemy import select

    async with fabrica_sessao() as sessao:
        resultado = await sessao.execute(
            select(Usuario).where(Usuario.id == UUID_ANONIMO)
        )
        if resultado.scalar_one_or_none() is None:
            usuario_anonimo = Usuario(
                id=UUID_ANONIMO,
                email="anonimo@trippin.internal",
                hashed_password="",
                is_active=True,
                is_verified=True,
                is_superuser=False,
                nome="Anônimo",
            )
            sessao.add(usuario_anonimo)
            await sessao.commit()


def criar_app() -> FastAPI:
    """
    Factory que constrói e configura a instância FastAPI.

    Usar factory (em vez de instanciar direto no módulo) facilita testes:
    cada teste pode chamar criar_app() e obter uma instância limpa.
    """
    app = FastAPI(
        title="Trippin' API",
        description="API de planejamento de viagens com IA",
        version="1.0.0",
        # Swagger e ReDoc ficam desabilitados em produção para não expor a API publicamente
        docs_url="/docs" if configuracoes.ambiente == "dev" else None,
        redoc_url="/redoc" if configuracoes.ambiente == "dev" else None,
        lifespan=ciclo_de_vida,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Necessário para o frontend Next.js (domínio diferente) fazer requisições ao backend.
    # Em produção, cors_origens deve conter apenas o domínio real (ex: https://trippin.com).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracoes.cors_origens,
        allow_credentials=True,  # necessário para envio de cookies/tokens
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate Limiting (slowapi) ───────────────────────────────────────────────
    # Por que slowapi?
    # - Wrapper sobre limits que integra nativamente com FastAPI
    # - Aplica limite por IP (get_remote_address) sem precisar de Redis separado
    # - Cada endpoint pode ter seu próprio limite via decorator @limitador.limit()
    # O limite de 5 requisições/hora para criação de viagens está no roteador de viagens.
    limitador = Limiter(key_func=get_remote_address)
    app.state.limiter = limitador
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    # Importados aqui (e não no topo do arquivo) para evitar imports circulares,
    # já que os routers dependem de modelos que dependem de config.
    from autenticacao.roteador import roteador_auth
    from compartilhamento.roteador import roteador_compartilhamento
    from locais.roteador import roteador_locais
    from monitoramento.roteador import roteador_monitoramento
    from viagens.roteador import roteador_viagens

    app.include_router(roteador_auth, prefix="/api")
    app.include_router(roteador_viagens, prefix="/api")
    app.include_router(roteador_compartilhamento, prefix="/api")
    app.include_router(roteador_locais, prefix="/api")
    app.include_router(roteador_monitoramento, prefix="/api")

    return app


# Instância global usada pelo uvicorn: `uvicorn main:app`
app = criar_app()
