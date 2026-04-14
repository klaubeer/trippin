"""
Router de monitoramento — histórico de execuções dos agentes IA.

Endpoints:
  GET /api/monitoramento/historico  → todas as solicitações com métricas agregadas
  GET /api/monitoramento/{id}/logs  → logs detalhados por agente de uma solicitação

Sem autenticação obrigatória neste router para facilitar o portfólio —
em produção, restringiria a superusuários ou adicionaria chave de API.
"""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from banco.sessao import obter_sessao
from monitoramento.modelos import LogExecucaoAgente
from viagens.modelos import SolicitacaoViagem

roteador_monitoramento = APIRouter(prefix="/monitoramento", tags=["monitoramento"])


@roteador_monitoramento.get("/historico")
async def listar_historico(
    sessao: AsyncSession = Depends(obter_sessao),
) -> list[dict]:
    """
    Retorna todas as solicitações com métricas agregadas de execução.

    Para cada solicitação inclui:
    - Dados básicos da viagem (destino, datas, status)
    - Métricas totais: tokens, custo USD, duração
    - Breakdown por agente (voos, hotéis, atividades, arquiteto)
    """
    # Carrega todas as solicitações com seus logs de execução
    resultado = await sessao.execute(
        select(SolicitacaoViagem)
        .order_by(SolicitacaoViagem.criado_em.desc())
        .limit(200)  # limita a 200 mais recentes para não sobrecarregar a UI
    )
    solicitacoes = resultado.scalars().all()

    if not solicitacoes:
        return []

    # Carrega logs agrupados por solicitacao_id em uma única query
    ids = [s.id for s in solicitacoes]
    logs_resultado = await sessao.execute(
        select(LogExecucaoAgente)
        .where(LogExecucaoAgente.solicitacao_id.in_(ids))
        .order_by(LogExecucaoAgente.iniciado_em)
    )
    todos_logs = logs_resultado.scalars().all()

    # Indexa logs por solicitacao_id para lookup O(1)
    logs_por_solicitacao: dict[uuid.UUID, list[LogExecucaoAgente]] = {}
    for log in todos_logs:
        logs_por_solicitacao.setdefault(log.solicitacao_id, []).append(log)

    historico = []
    for sol in solicitacoes:
        logs = logs_por_solicitacao.get(sol.id, [])

        # Agrega métricas de todos os agentes
        total_tokens_entrada = sum(l.tokens_entrada_estimado or 0 for l in logs)
        total_tokens_saida = sum(l.tokens_saida_estimado or 0 for l in logs)
        total_custo = sum(float(l.custo_usd_estimado or 0) for l in logs)
        total_duracao = sum(l.duracao_segundos or 0 for l in logs)

        # Breakdown por agente
        agentes_detalhes = [
            {
                "agente": log.agente.value,
                "modelo": log.modelo_llm,
                "status": log.status.value,
                "tokens_entrada": log.tokens_entrada_estimado,
                "tokens_saida": log.tokens_saida_estimado,
                "tokens_total": (log.tokens_entrada_estimado or 0) + (log.tokens_saida_estimado or 0),
                "custo_usd": float(log.custo_usd_estimado or 0),
                "duracao_segundos": log.duracao_segundos,
                "fonte_dados": log.fonte_dados,
            }
            for log in logs
        ]

        historico.append({
            "id": str(sol.id),
            "slug": str(sol.slug),
            "origem": sol.origem,
            "destino": sol.destino,
            "data_inicio": sol.data_inicio.isoformat(),
            "data_fim": sol.data_fim.isoformat(),
            "num_viajantes": sol.num_viajantes,
            "status": sol.status.value,
            "criado_em": sol.criado_em.isoformat(),
            "metricas": {
                "total_tokens_entrada": total_tokens_entrada,
                "total_tokens_saida": total_tokens_saida,
                "total_tokens": total_tokens_entrada + total_tokens_saida,
                "custo_usd": round(total_custo, 6),
                "duracao_total_segundos": round(total_duracao, 2),
            },
            "agentes": agentes_detalhes,
        })

    return historico
