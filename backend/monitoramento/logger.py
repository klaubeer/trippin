"""
Sistema de logging centralizado do Trippin'.

Três destinos de log:
  1. Arquivo rotativo (logs/trippin.log): tudo a partir de DEBUG — para análise offline
  2. Console: INFO+ — visível nos logs do Docker (`docker compose logs celery`)
  3. Banco de dados (tabela logs_execucao_agente): uma entrada por execução de agente,
     com duração, tokens estimados e custo — útil para monitorar uso e gastos

Por que logging padrão do Python em vez de loguru/structlog?
- Sem dependências extras
- Suficiente para o nível de observabilidade necessário no portfólio
- RotatingFileHandler evita que o arquivo de log cresça indefinidamente

Estimativa de tokens:
- CrewAI não expõe métricas de tokens diretamente no resultado
- Usamos heurística de ~4 chars/token — boa aproximação para PT/EN
- Custo estimado em USD para controle de gastos durante desenvolvimento
"""
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import time
from typing import Optional

# Garante que a pasta de logs existe antes de tentar criar o handler de arquivo
Path("logs").mkdir(exist_ok=True)

# ─── Configuração do logger Python ───────────────────────────────────────────

FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

# Logger raiz da aplicação — todos os sub-loggers herdam sua configuração
logger_raiz = logging.getLogger("trippin")
logger_raiz.setLevel(logging.DEBUG)

# Handler: arquivo rotativo (10 MB × 5 arquivos = até 50 MB de histórico)
handler_arquivo = RotatingFileHandler(
    "logs/trippin.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
handler_arquivo.setLevel(logging.DEBUG)
handler_arquivo.setFormatter(logging.Formatter(FORMATO, FORMATO_DATA))

# Handler: console — apenas INFO+ para não poluir os logs do Docker com DEBUG
handler_console = logging.StreamHandler()
handler_console.setLevel(logging.INFO)
handler_console.setFormatter(logging.Formatter(FORMATO, FORMATO_DATA))

logger_raiz.addHandler(handler_arquivo)
logger_raiz.addHandler(handler_console)


def obter_logger(nome: str) -> logging.Logger:
    """
    Retorna um logger filho hierárquico: `trippin.{nome}`.
    Herda configuração do logger_raiz mas pode ser filtrado individualmente.

    Uso: logger = obter_logger("agente.voos")  →  logger name: "trippin.agente.voos"
    """
    return logging.getLogger(f"trippin.{nome}")


# ─── Tabela de preços por modelo (USD por 1M tokens) ─────────────────────────
# Mantida aqui para fácil atualização quando os provedores mudam os preços.
# Formato: (preco_entrada, preco_saida)
PRECO_POR_MODELO = {
    "openai/gpt-4o-mini":                 (0.15,   0.60),  # $0.15/$0.60 por 1M tokens
    "openai/gpt-4.1-mini":                (0.40,   1.60),  # $0.40/$1.60 por 1M tokens
    # Modelos legados (mantidos para histórico de logs antigos)
    "groq/llama-3.1-8b-instant":          (0.05,   0.08),
    "gemini/gemini-1.5-flash":            (0.075,  0.30),
    "anthropic/claude-haiku-4-5-20251001": (0.80,  4.00),
}


def estimar_custo(modelo: str, tokens_entrada: int, tokens_saida: int) -> Decimal:
    """
    Estima o custo em USD baseado no número de tokens e preço do modelo.
    Usa (1.0, 1.0) como fallback para modelos não cadastrados.
    """
    preco = PRECO_POR_MODELO.get(modelo, (1.0, 1.0))
    custo = (tokens_entrada * preco[0] + tokens_saida * preco[1]) / 1_000_000
    return Decimal(str(round(custo, 6)))


def estimar_tokens(texto: str) -> int:
    """
    Estimativa de tokens por contagem de caracteres (~4 chars/token).
    Não é exata, mas suficiente para controle de gastos aproximado.
    max(1, ...) evita divisão por zero ou tokens negativos.
    """
    return max(1, len(texto) // 4)


# ─── Context manager para registro de execução de agente ─────────────────────

class ContextoExecucao:
    """
    Context manager que envolve a execução de um agente CrewAI,
    mede o tempo e persiste o resultado no banco de dados.

    Uso:
        with ContextoExecucao(solicitacao_id, "voos", "groq/llama-3.1-8b-instant", entrada) as ctx:
            resultado = executar_agente_voos(...)
            ctx.registrar_saida(json.dumps(resultado), fonte="amadeus")
        # ao sair do with: salva automaticamente no banco

    Se o agente lançar uma exceção, o context manager captura, registra como "falhou"
    e re-lança a exceção (return False no __exit__ não suprime).
    """

    def __init__(
        self,
        solicitacao_id: str,
        agente: str,
        modelo_llm: str,
        entrada_resumo: str = "",
    ):
        self.solicitacao_id = solicitacao_id
        self.agente = agente
        self.modelo_llm = modelo_llm
        self.entrada_resumo = entrada_resumo[:500]  # trunca para caber na coluna do banco
        self.log_id = uuid.uuid4()
        self._inicio = time()
        self._saida: Optional[str] = None
        self._fonte: str = "llm_gerado"
        self._erro: Optional[str] = None
        self._tokens_entrada_reais: Optional[int] = None  # tokens reais da API (OpenAI/Gemini)
        self._tokens_saida_reais: Optional[int] = None
        self.logger = obter_logger(f"agente.{agente}")

    def registrar_saida(
        self,
        saida: str,
        fonte: str = "llm_gerado",
        tokens_entrada: Optional[int] = None,
        tokens_saida: Optional[int] = None,
    ) -> None:
        """
        Registra o output do agente antes de sair do context manager.
        fonte: "amadeus" | "google_places" | "llm_gerado" | "mock"
        tokens_entrada/tokens_saida: valores reais reportados pela API (preferível à heurística).
        """
        self._saida = saida
        self._fonte = fonte
        if tokens_entrada is not None:
            self._tokens_entrada_reais = tokens_entrada
        if tokens_saida is not None:
            self._tokens_saida_reais = tokens_saida

    def __enter__(self):
        self.logger.info(
            f"[{self.agente.upper()}] Iniciando | solicitacao={self.solicitacao_id} | modelo={self.modelo_llm}"
        )
        return self

    def __exit__(self, tipo_exc, valor_exc, tb):
        duracao = round(time() - self._inicio, 2)
        status = "falhou" if tipo_exc else "concluido"

        if tipo_exc:
            self._erro = str(valor_exc)
            self.logger.error(
                f"[{self.agente.upper()}] FALHOU | {duracao}s | erro={self._erro}"
            )
        else:
            self.logger.info(
                f"[{self.agente.upper()}] Concluído | {duracao}s | fonte={self._fonte}"
            )

        # Persiste no banco — falha silenciosa para não mascarar erro do agente
        try:
            _salvar_log_banco(
                log_id=self.log_id,
                solicitacao_id=self.solicitacao_id,
                agente=self.agente,
                modelo_llm=self.modelo_llm,
                status=status,
                duracao_segundos=duracao,
                entrada_resumo=self.entrada_resumo,
                saida_resumo=(self._saida or "")[:2000],
                mensagem_erro=self._erro,
                fonte_dados=self._fonte,
                tokens_entrada_reais=self._tokens_entrada_reais,
                tokens_saida_reais=self._tokens_saida_reais,
            )
        except Exception as e:
            self.logger.warning(f"Falha ao salvar log no banco: {e}")

        return False  # não suprime exceções — o Celery precisa capturá-las


def _salvar_log_banco(
    log_id: uuid.UUID,
    solicitacao_id: str,
    agente: str,
    modelo_llm: str,
    status: str,
    duracao_segundos: float,
    entrada_resumo: str,
    saida_resumo: str,
    mensagem_erro: Optional[str],
    fonte_dados: str,
    tokens_entrada_reais: Optional[int] = None,
    tokens_saida_reais: Optional[int] = None,
) -> None:
    """
    Persiste o log de execução no banco usando conexão síncrona (Celery worker).
    Usa tokens reais da API quando disponíveis; heurística (~4 chars/token) como fallback.
    Importações locais evitam import circular com os modelos de monitoramento.
    """
    import sqlalchemy as sa
    from sqlalchemy.orm import Session
    from config import configuracoes
    from monitoramento.modelos import LogExecucaoAgente, NomeAgente, StatusExecucao

    # Prefere tokens reais (reportados pela API) sobre estimativa por heurística
    tokens_entrada = tokens_entrada_reais if tokens_entrada_reais is not None else estimar_tokens(entrada_resumo)
    tokens_saida = tokens_saida_reais if tokens_saida_reais is not None else estimar_tokens(saida_resumo)
    custo = estimar_custo(modelo_llm, tokens_entrada, tokens_saida)

    url_sincrona = configuracoes.database_url.replace("+asyncpg", "+psycopg2", 1)
    motor = sa.create_engine(url_sincrona)

    with Session(motor) as sessao:
        log = LogExecucaoAgente(
            id=log_id,
            solicitacao_id=uuid.UUID(solicitacao_id),
            agente=NomeAgente(agente),
            modelo_llm=modelo_llm,
            status=StatusExecucao(status),
            concluido_em=datetime.utcnow(),
            duracao_segundos=duracao_segundos,
            tokens_entrada_estimado=tokens_entrada,
            tokens_saida_estimado=tokens_saida,
            custo_usd_estimado=custo,
            entrada_resumo=entrada_resumo,
            saida_resumo=saida_resumo,
            mensagem_erro=mensagem_erro,
            fonte_dados=fonte_dados,
        )
        sessao.add(log)
        sessao.commit()

    motor.dispose()
