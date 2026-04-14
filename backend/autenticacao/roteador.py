"""
Router de autenticação — monta os endpoints gerados automaticamente pelo fastapi-users.

Endpoints registrados:
  POST /api/auth/login          → retorna JWT
  POST /api/auth/logout         → invalida sessão (no-op para JWT stateless)
  POST /api/auth/register       → cria conta nova
  POST /api/auth/verify         → confirma e-mail com token
  POST /api/auth/request-verify-token → reenviar e-mail de verificação
  POST /api/auth/forgot-password       → solicitar reset de senha
  POST /api/auth/reset-password        → redefinir senha com token
  GET  /api/usuarios/me         → dados do usuário logado
  PATCH /api/usuarios/me        → atualizar perfil
  GET  /api/usuarios/{id}       → admin: ver usuário por ID
  PATCH /api/usuarios/{id}      → admin: editar usuário por ID
"""
from fastapi import APIRouter

from .esquemas import EsquemaAtualizacaoUsuario, EsquemaCriacaoUsuario, EsquemaLeituraUsuario
from .gerenciador import backend_auth, fastapi_users

roteador_auth = APIRouter(tags=["autenticacao"])

# Endpoints de login/logout — usa o backend JWT configurado em gerenciador.py
roteador_auth.include_router(
    fastapi_users.get_auth_router(backend_auth),
    prefix="/auth",
)

# Endpoint de registro — recebe EsquemaCriacaoUsuario, retorna EsquemaLeituraUsuario
roteador_auth.include_router(
    fastapi_users.get_register_router(EsquemaLeituraUsuario, EsquemaCriacaoUsuario),
    prefix="/auth",
)

# Endpoints de verificação de e-mail
roteador_auth.include_router(
    fastapi_users.get_verify_router(EsquemaLeituraUsuario),
    prefix="/auth",
)

# Endpoints de reset de senha
roteador_auth.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
)

# Endpoints de gerenciamento do perfil (/me) e admin (/usuarios/{id})
roteador_auth.include_router(
    fastapi_users.get_users_router(EsquemaLeituraUsuario, EsquemaAtualizacaoUsuario),
    prefix="/usuarios",
)
