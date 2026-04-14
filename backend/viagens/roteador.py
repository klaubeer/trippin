"""
Router de viagens — endpoints CRUD e SSE para solicitações de roteiro.

Endpoints:
  POST /api/viagens/               → cria solicitação e dispara task Celery
  GET  /api/viagens/               → lista solicitações do usuário logado
  GET  /api/viagens/{id}           → retorna solicitação com todos os roteiros
  GET  /api/viagens/{id}/stream    → SSE: stream de progresso dos agentes
  GET  /api/viagens/{id}/roteiros/{nivel}/pdf → download do PDF

Por que SSE (Server-Sent Events) em vez de WebSocket?
- SSE é unidirecional: servidor → cliente. Para progresso, não precisamos de bidirec.
- Mais simples de implementar e de consumir no browser (EventSource nativo)
- sse-starlette integra com o event loop async do FastAPI sem overhead extra
- WebSocket seria over-engineering para este caso de uso

Por que Redis Pub/Sub para o SSE?
- O worker Celery roda em processo separado do FastAPI
- O worker não pode acessar diretamente as conexões SSE abertas no FastAPI
- Redis como mensageiro: worker publica eventos → FastAPI assina e faz o relay ao browser
"""
import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import redis.asyncio as redis_async

from autenticacao import (
    UUID_ANONIMO,
    Usuario,
    usuario_atual_ativo,
    usuario_atual_opcional,
    usuario_atual_via_query_opcional,
)
from banco.sessao import obter_sessao
from config import configuracoes

from .esquemas import EsquemaCriacaoSolicitacao, EsquemaSolicitacao, EsquemaSolicitacaoComRoteiros
from .modelos import Atividade, Hospedagem, Roteiro, SolicitacaoViagem, StatusSolicitacao, Voo

roteador_viagens = APIRouter(prefix="/viagens", tags=["viagens"])

# Instância local do limitador — o limite de 5/hora é aplicado por endpoint via decorator
limitador = Limiter(key_func=get_remote_address)


@roteador_viagens.post(
    "/",
    response_model=EsquemaSolicitacao,
    status_code=status.HTTP_201_CREATED,
)
@limitador.limit("5/hour")
async def criar_solicitacao(
    request: Request,
    dados: EsquemaCriacaoSolicitacao,
    usuario: Usuario | None = Depends(usuario_atual_opcional),
    sessao: AsyncSession = Depends(obter_sessao),
) -> SolicitacaoViagem:
    """
    Cria uma nova solicitação de viagem e dispara o processamento assíncrono.
    Funciona com ou sem autenticação — usuários anônimos usam UUID_ANONIMO como ID.
    Usuários logados têm o histórico vinculado à conta; anônimos não.
    """
    usuario_id = usuario.id if usuario else UUID_ANONIMO
    solicitacao = SolicitacaoViagem(
        usuario_id=usuario_id,
        origem=dados.origem,
        iata_origem=dados.iata_origem.upper(),
        destino=dados.destino,
        iata_destino=dados.iata_destino.upper(),
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        num_viajantes=dados.num_viajantes,
    )
    sessao.add(solicitacao)
    await sessao.commit()
    await sessao.refresh(solicitacao)

    # .delay() coloca a task na fila do Redis sem bloquear o request atual.
    # O Celery worker pega a task e executa em background (processo separado).
    from tarefas.gerar_roteiro import gerar_roteiro
    gerar_roteiro.delay(str(solicitacao.id))

    return solicitacao


@roteador_viagens.get("/", response_model=list[EsquemaSolicitacao])
async def listar_solicitacoes(
    usuario: Usuario = Depends(usuario_atual_ativo),
    sessao: AsyncSession = Depends(obter_sessao),
) -> list[SolicitacaoViagem]:
    """
    Lista todas as solicitações do usuário logado, ordenadas da mais recente para a mais antiga.
    Usado na tela "Minhas Viagens".
    """
    resultado = await sessao.execute(
        select(SolicitacaoViagem)
        .where(SolicitacaoViagem.usuario_id == usuario.id)
        .order_by(SolicitacaoViagem.criado_em.desc())
    )
    return list(resultado.scalars().all())


@roteador_viagens.get("/{id}", response_model=EsquemaSolicitacaoComRoteiros)
async def obter_solicitacao(
    id: uuid.UUID,
    usuario: Usuario | None = Depends(usuario_atual_opcional),
    sessao: AsyncSession = Depends(obter_sessao),
) -> SolicitacaoViagem:
    """
    Retorna uma solicitação completa com os 3 roteiros e todos os dados aninhados.
    Usuários logados: só veem as próprias solicitações.
    Anônimos: podem ver qualquer solicitação pelo ID (sem histórico, sem proteção de posse).
    """
    usuario_id = usuario.id if usuario else UUID_ANONIMO
    resultado = await sessao.execute(
        select(SolicitacaoViagem)
        .where(SolicitacaoViagem.id == id, SolicitacaoViagem.usuario_id == usuario_id)
        .options(
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.voos),
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.hospedagens),
            selectinload(SolicitacaoViagem.roteiros).selectinload(Roteiro.atividades),
        )
    )
    solicitacao = resultado.scalar_one_or_none()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return solicitacao


@roteador_viagens.get("/{id}/stream")
async def stream_progresso(
    id: uuid.UUID,
    request: Request,
    usuario: Usuario | None = Depends(usuario_atual_via_query_opcional),
    sessao: AsyncSession = Depends(obter_sessao),
) -> EventSourceResponse:
    """
    Endpoint SSE que transmite progresso dos agentes em tempo real.
    Funciona sem autenticação — token opcional via ?token=.

    Protocolo de eventos publicados pelo Celery worker:
      {"agente": "voos", "status": "iniciando"}
      {"agente": "voos", "status": "concluido"}
      ... (repete para hoteis, atividades, arquiteto)
      {"tipo": "finalizado", "solicitacao_id": "..."}  ← frontend redireciona para /roteiros/{id}
      {"tipo": "erro", "mensagem": "..."}               ← frontend exibe mensagem de erro

    O gerador `gerador_eventos` fica ativo enquanto o browser estiver conectado.
    Se o browser desconectar (aba fechada), `request.is_disconnected()` retorna True
    e o gerador encerra, liberando a conexão Redis.
    """
    usuario_id = usuario.id if usuario else UUID_ANONIMO
    resultado = await sessao.execute(
        select(SolicitacaoViagem).where(
            SolicitacaoViagem.id == id, SolicitacaoViagem.usuario_id == usuario_id
        )
    )
    if not resultado.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    async def gerador_eventos():
        # Canal Redis específico para esta solicitação — cada viagem tem seu canal isolado
        canal = f"progresso:{id}"
        cliente_redis = redis_async.from_url(configuracoes.redis_url)
        pubsub = cliente_redis.pubsub()
        await pubsub.subscribe(canal)

        try:
            async for mensagem in pubsub.listen():
                # Verifica desconexão do browser a cada mensagem
                if await request.is_disconnected():
                    break
                if mensagem["type"] == "message":
                    dados = json.loads(mensagem["data"])
                    yield {"data": json.dumps(dados)}
                    # Encerra o stream após evento final (sucesso ou erro)
                    if dados.get("tipo") in ("finalizado", "erro"):
                        break
        finally:
            # Limpa a inscrição Redis ao encerrar — evita memory leak
            await pubsub.unsubscribe(canal)
            await cliente_redis.aclose()

    return EventSourceResponse(gerador_eventos())


@roteador_viagens.get("/{id}/roteiros/{nivel}/pdf")
async def baixar_pdf_roteiro(
    id: uuid.UUID,
    nivel: str,
    usuario: Usuario = Depends(usuario_atual_ativo),
    sessao: AsyncSession = Depends(obter_sessao),
):
    """
    Gera e retorna o PDF de um roteiro específico.

    Fluxo:
    1. Valida que a solicitação e o roteiro pertencem ao usuário
    2. Carrega todos os dados do roteiro (voos, hospedagens, atividades)
    3. Chama gerar_pdf_roteiro() do módulo pdf/gerador.py (reportlab)
    4. Retorna os bytes como attachment com Content-Disposition

    Por que reportlab?
    - Biblioteca Python madura para geração de PDF programático
    - Não depende de browser/puppeteer — roda no servidor sem display
    - Suficiente para o nível de formatação necessário no portfólio
    """
    from fastapi.responses import Response
    from sqlalchemy.orm import selectinload
    from viagens.modelos import NivelRoteiro

    try:
        nivel_enum = NivelRoteiro(nivel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nível inválido. Use: economico, conforto ou premium")

    resultado_solicitacao = await sessao.execute(
        select(SolicitacaoViagem)
        .where(SolicitacaoViagem.id == id, SolicitacaoViagem.usuario_id == usuario.id)
    )
    solicitacao = resultado_solicitacao.scalar_one_or_none()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    from viagens.modelos import Roteiro
    resultado_roteiro = await sessao.execute(
        select(Roteiro)
        .where(Roteiro.solicitacao_id == id, Roteiro.nivel == nivel_enum)
        .options(
            selectinload(Roteiro.voos),
            selectinload(Roteiro.hospedagens),
            selectinload(Roteiro.atividades),
        )
    )
    roteiro = resultado_roteiro.scalar_one_or_none()
    if not roteiro:
        raise HTTPException(status_code=404, detail="Roteiro não encontrado")

    from pdf.gerador import gerar_pdf_roteiro
    pdf_bytes = gerar_pdf_roteiro(solicitacao, roteiro)

    nome_arquivo = f"trippin-{solicitacao.destino.lower().replace(' ', '-')}-{nivel}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
