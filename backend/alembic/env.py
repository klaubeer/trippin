import asyncio
import sys
import os
from logging.config import fileConfig

# Garante que /app (raiz do backend) está no Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importar todos os modelos para que o Alembic os detecte
from banco.base import Base  # noqa: F401
import autenticacao.modelos  # noqa: F401
import viagens.modelos  # noqa: F401
import monitoramento.modelos  # noqa: F401

from config import configuracoes

config = context.config
config.set_main_option("sqlalchemy.url", configuracoes.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def rodar_migracoes_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def rodar_migracoes_online(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def rodar_async() -> None:
    motor = create_async_engine(configuracoes.database_url)
    async with motor.connect() as conn:
        await conn.run_sync(rodar_migracoes_online)
    await motor.dispose()


if context.is_offline_mode():
    rodar_migracoes_offline()
else:
    asyncio.run(rodar_async())
