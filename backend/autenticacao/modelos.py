"""
Modelo de usuário da aplicação.

Por que fastapi-users?
- Implementa do zero: registro, login, JWT, verificação de e-mail, reset de senha
- Evita reinventar a roda para auth — problema resolvido, bem testado
- SQLAlchemyBaseUserTableUUID já define as colunas padrão:
  id (UUID), email, hashed_password, is_active, is_superuser, is_verified
- Basta herdar e adicionar campos específicos do projeto (ex: nome)
"""
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy.orm import Mapped, mapped_column

from banco.base import Base


class Usuario(SQLAlchemyBaseUserTableUUID, Base):
    """
    Tabela `usuarios` — estende o modelo base do fastapi-users.

    Colunas herdadas automaticamente:
      - id: UUID (PK)
      - email: str (único)
      - hashed_password: str
      - is_active: bool
      - is_superuser: bool
      - is_verified: bool

    Colunas adicionadas:
      - nome: exibido no perfil e nos roteiros gerados
    """
    __tablename__ = "usuarios"

    nome: Mapped[str] = mapped_column(nullable=False, default="")
