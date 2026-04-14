"""
Núcleo da autenticação — configuração do fastapi-users.

Componentes:
  - GerenciadorUsuario: lógica de negócio pós-eventos (registro, senha, verificação)
  - obter_estrategia_jwt: gera/valida tokens JWT com expiração configurável
  - backend_auth: combina transporte (Bearer header) + estratégia (JWT)
  - fastapi_users: instância principal que gera os routers de auth automaticamente
  - usuario_atual_ativo: dependência usada nos endpoints protegidos
  - usuario_atual_via_query: variação para SSE (browsers não suportam headers em EventSource)
"""
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from banco.sessao import obter_sessao
from config import configuracoes

from .modelos import Usuario


async def obter_banco_usuario(sessao: AsyncSession = Depends(obter_sessao)):
    """
    Dependência que fornece o adaptador de banco para fastapi-users.
    SQLAlchemyUserDatabase traduz as operações de usuário para queries SQL.
    """
    yield SQLAlchemyUserDatabase(sessao, Usuario)


class GerenciadorUsuario(UUIDIDMixin, BaseUserManager[Usuario, uuid.UUID]):
    """
    Ponto de extensão do ciclo de vida de usuários.

    UUIDIDMixin configura o tipo do ID como UUID (em vez de int).
    Os métodos on_after_* são hooks chamados automaticamente pelo fastapi-users
    — aqui apenas logamos no terminal, mas em produção enviaríamos e-mails.
    """

    # Os tokens de reset/verificação usam o mesmo segredo do JWT para simplificar
    reset_password_token_secret = configuracoes.jwt_secret
    verification_token_secret = configuracoes.jwt_secret

    async def on_after_register(self, usuario: Usuario, request: Optional[Request] = None):
        """Chamado após cadastro bem-sucedido. Em produção: enviar e-mail de boas-vindas."""
        print(f"Usuário registrado: {usuario.email}")

    async def on_after_forgot_password(
        self, usuario: Usuario, token: str, request: Optional[Request] = None
    ):
        """Chamado quando o usuário solicita reset de senha. Em produção: enviar e-mail com link."""
        print(f"Token de redefinição para {usuario.email}: {token}")

    async def on_after_request_verify(
        self, usuario: Usuario, token: str, request: Optional[Request] = None
    ):
        """Chamado quando o usuário solicita verificação de e-mail. Em produção: enviar e-mail."""
        print(f"Token de verificação para {usuario.email}: {token}")


async def obter_gerenciador_usuario(
    banco_usuario=Depends(obter_banco_usuario),
):
    """Dependência que fornece uma instância do GerenciadorUsuario por request."""
    yield GerenciadorUsuario(banco_usuario)


def obter_estrategia_jwt() -> JWTStrategy:
    """
    Cria a estratégia JWT com as configurações do .env.
    JWTStrategy assina os tokens com HS256 e valida expiração automaticamente.
    """
    return JWTStrategy(
        secret=configuracoes.jwt_secret,
        lifetime_seconds=configuracoes.jwt_expiracao_minutos * 60,
    )


# BearerTransport: token enviado no header `Authorization: Bearer <token>`
# tokenUrl aponta para o endpoint de login — usado para documentação Swagger
transporte_bearer = BearerTransport(tokenUrl="/api/auth/login")

# backend_auth combina transporte + estratégia em um objeto que o fastapi-users usa
# para autenticar requests e gerar/validar tokens
backend_auth = AuthenticationBackend(
    name="jwt",
    transport=transporte_bearer,
    get_strategy=obter_estrategia_jwt,
)

# Instância principal do fastapi-users — gera automaticamente os routers de
# login, registro, verificação, reset de senha e gerenciamento de usuários
fastapi_users = FastAPIUsers[Usuario, uuid.UUID](
    obter_gerenciador_usuario,
    [backend_auth],
)

# Dependências prontas para usar nos endpoints:
usuario_atual_ativo = fastapi_users.current_user(active=True)
usuario_atual_superuser = fastapi_users.current_user(active=True, superuser=True)


# UUID fixo para solicitações anônimas — sem precisar de migration
UUID_ANONIMO = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Dependência opcional: retorna o usuário se autenticado, None se anônimo
usuario_atual_opcional = fastapi_users.current_user(active=True, optional=True)


async def usuario_atual_via_query(
    token: str = Query(..., description="JWT de autenticação (para SSE)"),
    sessao: AsyncSession = Depends(obter_sessao),
) -> Usuario:
    """
    Dependência alternativa para endpoints SSE (Server-Sent Events).

    Por que não usar o header Authorization padrão?
    A API EventSource do browser não suporta headers customizados —
    ela sempre faz um GET simples sem poder definir Authorization.
    Solução: o frontend passa o JWT como query param `?token=...`.

    Uso: GET /api/viagens/{id}/stream?token=<jwt>
    """
    estrategia = obter_estrategia_jwt()
    try:
        usuario = await estrategia.read_token(token, SQLAlchemyUserDatabase(sessao, Usuario))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    if usuario is None or not usuario.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    return usuario


async def usuario_atual_via_query_opcional(
    token: Optional[str] = Query(None, description="JWT de autenticação (opcional para SSE)"),
    sessao: AsyncSession = Depends(obter_sessao),
) -> Optional[Usuario]:
    """
    Versão opcional do usuario_atual_via_query.
    Retorna None se token ausente ou inválido — permite SSE sem autenticação.
    """
    if not token:
        return None
    estrategia = obter_estrategia_jwt()
    try:
        usuario = await estrategia.read_token(token, SQLAlchemyUserDatabase(sessao, Usuario))
        if usuario and usuario.is_active:
            return usuario
    except Exception:
        pass
    return None
