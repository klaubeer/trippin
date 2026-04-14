"""
Gerenciamento de sessões assíncronas do SQLAlchemy.

Por que async?
- FastAPI é totalmente async; usar sessões síncronas bloquearia o event loop
  durante queries ao banco, degradando performance sob carga
- asyncpg é o driver mais rápido para PostgreSQL em Python async

Fluxo de uso:
  1. FastAPI injeta `obter_sessao` como dependência via Depends()
  2. A sessão é aberta no início do request e fechada automaticamente ao final
  3. Cada request tem sua própria sessão — sem compartilhamento entre requests
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import configuracoes

# Motor de conexão com o banco.
# echo=True em dev imprime todo SQL gerado no terminal — útil para debug.
# pool_pre_ping=True testa a conexão antes de usar — evita erros após idle timeout do Postgres.
motor = create_async_engine(
    configuracoes.database_url,
    echo=configuracoes.ambiente == "dev",
    pool_pre_ping=True,
)

# Fábrica de sessões.
# expire_on_commit=False evita que atributos dos objetos fiquem "expirados"
# após um commit — essencial em APIs async onde você acessa os dados depois do commit.
fabrica_sessao = async_sessionmaker(motor, expire_on_commit=False)


async def obter_sessao() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência FastAPI que fornece uma sessão de banco de dados por request.
    O `async with` garante que a sessão é sempre fechada, mesmo em caso de exceção.

    Uso nos endpoints:
        async def meu_endpoint(sessao: AsyncSession = Depends(obter_sessao)):
            ...
    """
    async with fabrica_sessao() as sessao:
        yield sessao
