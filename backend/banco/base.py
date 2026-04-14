"""
Base declarativa do SQLAlchemy.

Todos os modelos ORM herdam desta classe — ela mantém o registro
de metadados (tabelas, colunas, relacionamentos) usado pelo Alembic
para detectar mudanças e gerar migrations automaticamente.

Por que SQLAlchemy 2.0?
- API moderna com typed mapped_column (MyPy-friendly, sem magic)
- Suporte async nativo via AsyncSession + asyncpg
- Alembic de migração padrão da indústria para projetos Python não-Django
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
