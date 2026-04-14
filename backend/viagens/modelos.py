"""
Modelos ORM das viagens — tabelas centrais da aplicação.

Hierarquia de dados:
  SolicitacaoViagem (1)
    └── Roteiro (3: economico, conforto, premium)
          ├── Voo (1 por roteiro)
          ├── Hospedagem (1 por roteiro)
          └── Atividade (N por roteiro — 2 por dia)

Por que SQLAlchemy 2.0 com Mapped[] e mapped_column()?
- Typed: IDE e MyPy conhecem os tipos das colunas sem precisar de stubs
- Declarativo moderno: sem magic de atributos — o que você lê é o que existe
- cascade="all, delete-orphan" nos relationships garante que ao deletar
  uma SolicitacaoViagem, todos os Roteiros/Voos/etc são removidos junto
"""
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from banco.base import Base


class StatusSolicitacao(str, PyEnum):
    """
    Ciclo de vida de uma solicitação de viagem:
    pendente → processando → concluido
                          ↘ falhou
    """
    pendente = "pendente"       # criada, aguardando o worker Celery pegar
    processando = "processando" # worker está rodando os 4 agentes
    concluido = "concluido"     # todos os roteiros salvos no banco
    falhou = "falhou"           # algum agente lançou exceção


class NivelRoteiro(str, PyEnum):
    """Três perfis de viagem gerados por cada solicitação."""
    economico = "economico"
    conforto = "conforto"
    premium = "premium"


class SolicitacaoViagem(Base):
    """
    Representa uma requisição de planejamento de viagem feita pelo usuário.
    É o ponto de entrada — criada no POST /api/viagens/ e processada pelo Celery.

    slug: UUID gerado automaticamente, usado para compartilhamento público
    sem expor o ID interno da solicitação.
    """
    __tablename__ = "solicitacoes_viagem"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    # Origem e destino — IATA é o código de 3 letras do aeroporto (ex: GRU, CDG, JFK)
    origem: Mapped[str] = mapped_column(String(200), nullable=False, default="São Paulo")
    iata_origem: Mapped[str] = mapped_column(String(3), nullable=False, default="GRU")
    destino: Mapped[str] = mapped_column(String(200), nullable=False)
    iata_destino: Mapped[str] = mapped_column(String(3), nullable=False)

    data_inicio: Mapped[date] = mapped_column(nullable=False)
    data_fim: Mapped[date] = mapped_column(nullable=False)
    num_viajantes: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[StatusSolicitacao] = mapped_column(
        Enum(StatusSolicitacao), nullable=False, default=StatusSolicitacao.pendente
    )

    # UUID único para compartilhamento público — acessível sem autenticação via /api/compartilhar/{slug}
    slug: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, unique=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    roteiros: Mapped[list["Roteiro"]] = relationship(back_populates="solicitacao", cascade="all, delete-orphan")


class Roteiro(Base):
    """
    Um dos 3 roteiros gerados (econômico, conforto ou premium).
    Contém o resumo textual e custo total calculado pelo agente arquiteto.
    """
    __tablename__ = "roteiros"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    solicitacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solicitacoes_viagem.id"), nullable=False
    )
    nivel: Mapped[NivelRoteiro] = mapped_column(Enum(NivelRoteiro), nullable=False)
    custo_total_estimado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    resumo: Mapped[str] = mapped_column(Text, nullable=True)  # 2 frases geradas pelo arquiteto GPT-4o-mini
    criado_em: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    solicitacao: Mapped["SolicitacaoViagem"] = relationship(back_populates="roteiros")
    voos: Mapped[list["Voo"]] = relationship(back_populates="roteiro", cascade="all, delete-orphan")
    hospedagens: Mapped[list["Hospedagem"]] = relationship(back_populates="roteiro", cascade="all, delete-orphan")
    atividades: Mapped[list["Atividade"]] = relationship(back_populates="roteiro", cascade="all, delete-orphan")


class Voo(Base):
    """
    Opção de voo associada a um roteiro.
    Dados fornecidos pela Amadeus API ou gerados pelo agente Groq/Llama.
    link_reserva é null porque a Amadeus sandbox não fornece links reais.
    """
    __tablename__ = "voos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roteiro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roteiros.id"), nullable=False)
    companhia: Mapped[str] = mapped_column(String(100), nullable=False)
    partida: Mapped[datetime] = mapped_column(nullable=False)
    chegada: Mapped[datetime] = mapped_column(nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    link_reserva: Mapped[str] = mapped_column(String(500), nullable=True)

    roteiro: Mapped["Roteiro"] = relationship(back_populates="voos")


class Hospedagem(Base):
    """
    Opção de hotel/hostel associada a um roteiro.
    Dados fornecidos pela Amadeus Hotel Search API ou gerados pelo agente Gemini.
    """
    __tablename__ = "hospedagens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roteiro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roteiros.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(100), nullable=True)        # ex: "Hostel", "Hotel 4★", "Resort"
    preco_por_noite: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    avaliacao: Mapped[float] = mapped_column(nullable=True)              # escala 0-5
    link_reserva: Mapped[str] = mapped_column(String(500), nullable=True)

    roteiro: Mapped["Roteiro"] = relationship(back_populates="hospedagens")


class Atividade(Base):
    """
    Uma atividade/atração dentro de um roteiro, organizada por dia.
    Coordenadas são usadas pelo componente Leaflet no frontend para plotar no mapa.
    Dados fornecidos pelo Google Places API ou gerados pelo agente Claude Haiku.
    """
    __tablename__ = "atividades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roteiro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roteiros.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    dia: Mapped[int] = mapped_column(nullable=False)             # 1, 2, 3... (dia da viagem)
    horario: Mapped[time] = mapped_column(nullable=True)         # ex: 09:00, 15:00
    descricao: Mapped[str] = mapped_column(Text, nullable=True)
    custo_estimado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=True)
    longitude: Mapped[float] = mapped_column(nullable=True)

    roteiro: Mapped["Roteiro"] = relationship(back_populates="atividades")
