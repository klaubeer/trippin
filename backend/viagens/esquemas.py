"""
Schemas Pydantic para as viagens — validação de entrada e serialização de saída.

Por que Pydantic v2?
- Validação automática de tipos na borda do sistema (antes de tocar o banco)
- Erros descritivos retornados como JSON 422 — frontend pode exibir mensagens exatas
- field_validator e model_validator permitem regras de negócio sem código extra nos endpoints

Separação de responsabilidades:
- EsquemaCriacaoSolicitacao: valida o body do POST /api/viagens/
- EsquemaVoo / EsquemaHospedagem / etc: serializam objetos ORM para JSON (model_config from_attributes)
- EsquemaSolicitacaoComRoteiros: resposta completa do GET /api/viagens/{id} com todos os dados aninhados
"""
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

from .modelos import NivelRoteiro, StatusSolicitacao


class EsquemaCriacaoSolicitacao(BaseModel):
    """
    Dados recebidos quando o usuário submete o formulário de planejamento.
    Todas as validações de negócio ficam aqui — nenhuma regra no endpoint.
    """
    origem: str = "São Paulo"
    iata_origem: str = "GRU"
    destino: str
    iata_destino: str
    data_inicio: date
    data_fim: date
    num_viajantes: int = 1

    @field_validator("data_inicio")
    @classmethod
    def data_inicio_futura(cls, v: date) -> date:
        """Impede agendamento de viagens para datas passadas."""
        from datetime import date as Date
        if v <= Date.today():
            raise ValueError("A data de ida deve ser no futuro")
        return v

    @field_validator("num_viajantes")
    @classmethod
    def viajantes_positivo(cls, v: int) -> int:
        """Garante que o número de viajantes está dentro dos limites suportados."""
        if v < 1:
            raise ValueError("O número de viajantes deve ser pelo menos 1")
        if v > 9:
            raise ValueError("O número máximo de viajantes é 9")
        return v

    @model_validator(mode="after")
    def validar_datas(self) -> "EsquemaCriacaoSolicitacao":
        """
        Validações que dependem de múltiplos campos:
        - data_fim deve ser depois de data_inicio
        - duração máxima de 30 dias (limita o volume de atividades geradas)
        """
        if self.data_fim <= self.data_inicio:
            raise ValueError("A data de volta deve ser após a data de ida")
        duracao = (self.data_fim - self.data_inicio).days
        if duracao > 30:
            raise ValueError("A viagem pode ter no máximo 30 dias")
        return self


class EsquemaVoo(BaseModel):
    id: uuid.UUID
    companhia: str
    partida: datetime
    chegada: datetime
    preco: Decimal
    link_reserva: str | None

    # from_attributes=True permite criar o schema diretamente de um objeto ORM
    model_config = {"from_attributes": True}


class EsquemaHospedagem(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str | None
    preco_por_noite: Decimal
    avaliacao: float | None
    link_reserva: str | None

    model_config = {"from_attributes": True}


class EsquemaAtividade(BaseModel):
    id: uuid.UUID
    nome: str
    dia: int
    horario: time | None
    descricao: str | None
    custo_estimado: Decimal | None
    latitude: float | None
    longitude: float | None

    model_config = {"from_attributes": True}


class EsquemaRoteiro(BaseModel):
    """Roteiro completo com voos, hospedagens e atividades aninhados."""
    id: uuid.UUID
    nivel: NivelRoteiro
    custo_total_estimado: Decimal | None
    resumo: str | None
    voos: list[EsquemaVoo] = []
    hospedagens: list[EsquemaHospedagem] = []
    atividades: list[EsquemaAtividade] = []

    model_config = {"from_attributes": True}


class EsquemaSolicitacao(BaseModel):
    """Dados resumidos de uma solicitação — usado na listagem GET /api/viagens/"""
    id: uuid.UUID
    origem: str
    iata_origem: str
    destino: str
    iata_destino: str
    data_inicio: date
    data_fim: date
    num_viajantes: int
    status: StatusSolicitacao
    slug: uuid.UUID
    criado_em: datetime

    model_config = {"from_attributes": True}


class EsquemaSolicitacaoComRoteiros(EsquemaSolicitacao):
    """
    Resposta completa do GET /api/viagens/{id} — inclui os 3 roteiros com todos os dados.
    Herda EsquemaSolicitacao e adiciona os roteiros aninhados.
    """
    roteiros: list[EsquemaRoteiro] = []
