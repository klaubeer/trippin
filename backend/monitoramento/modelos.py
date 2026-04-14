"""
Modelos de auditoria e observabilidade dos agentes IA.

Por que logar execuções no banco?
- Permite analisar custo real por viagem gerada (tokens × preço do modelo)
- Rastrear qual fonte foi usada (Amadeus, Google Places ou LLM gerado)
- Depurar falhas de agentes consultando entrada/saída
- Monitorar degradação de performance (aumento de duracao_segundos)

Estes logs são gerados pelo ContextoExecucao em monitoramento/logger.py
e consultáveis via SQL direto no PostgreSQL durante desenvolvimento.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum

from banco.base import Base


class NomeAgente(str, PyEnum):
    """Identificadores dos 4 agentes — usados como chave nos logs."""
    voos = "voos"
    hoteis = "hoteis"
    atividades = "atividades"
    arquiteto = "arquiteto"


class StatusExecucao(str, PyEnum):
    """Status do resultado da execução do agente."""
    iniciado = "iniciado"
    concluido = "concluido"
    falhou = "falhou"


class LogExecucaoAgente(Base):
    """
    Registra cada execução de agente CrewAI para observabilidade e controle de custos.

    Campos de diagnóstico:
    - entrada_resumo: primeiros 500 chars do input enviado ao agente
    - saida_resumo: primeiros 2000 chars do output retornado
    - mensagem_erro: stack trace ou mensagem se status == "falhou"
    - fonte_dados: indica se os dados vieram de API real ou foram gerados pelo LLM
    """
    __tablename__ = "logs_execucao_agente"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # ondelete="CASCADE": ao deletar a solicitação, os logs são removidos automaticamente
    solicitacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitacoes_viagem.id", ondelete="CASCADE"), nullable=False
    )
    agente: Mapped[NomeAgente] = mapped_column(Enum(NomeAgente), nullable=False)
    modelo_llm: Mapped[str] = mapped_column(String(100), nullable=False)  # ex: "groq/llama-3.1-8b-instant"
    status: Mapped[StatusExecucao] = mapped_column(
        Enum(StatusExecucao), nullable=False, default=StatusExecucao.iniciado
    )
    iniciado_em: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    concluido_em: Mapped[datetime] = mapped_column(nullable=True)
    duracao_segundos: Mapped[float] = mapped_column(nullable=True)

    # Estimativas de tokens — CrewAI não expõe tokens diretamente, calculamos por heurística
    tokens_entrada_estimado: Mapped[int] = mapped_column(nullable=True)
    tokens_saida_estimado: Mapped[int] = mapped_column(nullable=True)
    custo_usd_estimado: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=True)

    # Payloads para debug (truncados para evitar colunas gigantes)
    entrada_resumo: Mapped[str] = mapped_column(String(500), nullable=True)
    saida_resumo: Mapped[str] = mapped_column(Text, nullable=True)
    mensagem_erro: Mapped[str] = mapped_column(Text, nullable=True)
    # "amadeus" | "google_places" | "llm_gerado" | "mock"
    fonte_dados: Mapped[str] = mapped_column(String(50), nullable=True)
