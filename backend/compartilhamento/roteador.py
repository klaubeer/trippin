"""
Router de compartilhamento — acesso público a roteiros sem autenticação.

Permite que um usuário compartilhe seu roteiro com qualquer pessoa via URL:
  /api/compartilhar/{slug}

O `slug` é um UUID gerado automaticamente na criação da solicitação (diferente do `id`).
Usar um slug separado do ID primário é uma medida de segurança:
- O ID é sequencial/previsível e está em URLs autenticadas
- O slug é aleatório — impossível de adivinhar sem ter recebido o link
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from banco.sessao import obter_sessao
from viagens.esquemas import EsquemaSolicitacaoComRoteiros
from viagens.modelos import Roteiro, SolicitacaoViagem

roteador_compartilhamento = APIRouter(prefix="/compartilhar", tags=["compartilhamento"])


@roteador_compartilhamento.get("/{slug}", response_model=EsquemaSolicitacaoComRoteiros)
async def obter_roteiro_publico(
    slug: uuid.UUID,
    sessao: AsyncSession = Depends(obter_sessao),
) -> SolicitacaoViagem:
    """
    Retorna um roteiro completo via slug público — sem autenticação necessária.
    Usado pela página /share/{slug} no frontend, acessível por qualquer pessoa com o link.

    Carrega todos os dados aninhados (roteiros, voos, hospedagens, atividades)
    com selectinload para evitar N+1 queries.
    """
    resultado = await sessao.execute(
        select(SolicitacaoViagem)
        .where(SolicitacaoViagem.slug == slug)
        .options(
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.voos),
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.hospedagens),
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.atividades),
        )
    )
    solicitacao = resultado.scalar_one_or_none()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Roteiro não encontrado")
    return solicitacao
