"""
Schemas Pydantic para operações de usuário.

fastapi-users fornece schemas base que definem os campos padrão de auth
(email, password, is_active, etc.). Aqui estendemos cada um com o campo
`nome` específico do Trippin'.

- EsquemaLeituraUsuario: retornado nas respostas de GET /auth/me
- EsquemaCriacaoUsuario: recebido no body de POST /auth/register
- EsquemaAtualizacaoUsuario: recebido no body de PATCH /usuarios/{id}
"""
import uuid

from fastapi_users import schemas


class EsquemaLeituraUsuario(schemas.BaseUser[uuid.UUID]):
    """Dados do usuário retornados pela API (nunca inclui a senha)."""
    nome: str


class EsquemaCriacaoUsuario(schemas.BaseUserCreate):
    """Dados exigidos no cadastro: e-mail, senha e nome."""
    nome: str


class EsquemaAtualizacaoUsuario(schemas.BaseUserUpdate):
    """Campos que podem ser alterados pelo usuário. Todos opcionais."""
    nome: str | None = None
