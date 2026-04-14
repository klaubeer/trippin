"""
Task Celery principal: orquestra os 4 agentes CrewAI e salva os roteiros no banco.
Publica eventos de progresso no Redis para o endpoint SSE consumir.

Fluxo completo:
  1. Worker recebe o solicitacao_id da fila Redis
  2. Carrega os dados da solicitação do banco (conexão síncrona — Celery não é async)
  3. Executa os 4 agentes em sequência:
     a. Agente Voos (Groq Llama) → opções de voo por tier
     b. Agente Hotéis (Gemini Flash) → opções de hotel por tier
     c. Agente Atividades (Claude Haiku) → lista de atividades por dia
     d. Arquiteto (GPT-4o-mini) → sintetiza em 3 roteiros com resumo e custo total
  4. Salva os roteiros no banco
  5. Publica evento "finalizado" no Redis → SSE entrega ao browser → frontend redireciona

Por que conexão síncrona no Celery?
- Celery não roda no event loop do asyncio — usar asyncpg diretamente quebraria
- Solução: troca "+asyncpg" por "+psycopg2" na URL para ter uma engine síncrona
- Cada função helper (_carregar, _salvar, _atualizar) cria e descarta sua própria engine
"""
import json
import uuid

import redis as redis_sync

from config import configuracoes
from monitoramento.logger import ContextoExecucao, obter_logger
from tarefas.worker import app_celery

# Importar todos os modelos para que o SQLAlchemy conheça todas as tabelas
# e consiga resolver as foreign keys (ex: solicitacoes_viagem → usuarios)
import autenticacao.modelos  # noqa
import monitoramento.modelos  # noqa
import viagens.modelos  # noqa

logger = obter_logger("tarefa.gerar_roteiro")


def _publicar_evento(canal: str, evento: dict) -> None:
    """
    Publica um evento de progresso no canal Redis da solicitação.
    O endpoint SSE está inscrito neste canal e faz o relay ao browser.
    Usa conexão síncrona — não precisamos de async aqui (Celery worker).
    """
    cliente_redis = redis_sync.from_url(configuracoes.redis_url)
    cliente_redis.publish(canal, json.dumps(evento))
    cliente_redis.close()


def _carregar_solicitacao(solicitacao_id: str) -> dict:
    """
    Carrega os dados necessários para a geração do roteiro a partir do banco.
    Retorna um dicionário simples (em vez do objeto ORM) para evitar
    problemas de sessão ao passar entre funções.
    """
    import sqlalchemy as sa
    from sqlalchemy.orm import Session
    from viagens.modelos import SolicitacaoViagem

    # Troca o driver async (asyncpg) pelo síncrono (psycopg2) para compatibilidade com Celery
    url_sincrona = configuracoes.database_url.replace("+asyncpg", "+psycopg2", 1)
    motor = sa.create_engine(url_sincrona)
    with Session(motor) as sessao:
        solicitacao = sessao.get(SolicitacaoViagem, uuid.UUID(solicitacao_id))
        if not solicitacao:
            raise ValueError(f"Solicitação {solicitacao_id} não encontrada")
        dados = {
            "origem": solicitacao.origem,
            "iata_origem": solicitacao.iata_origem,
            "iata_destino": solicitacao.iata_destino,
            "destino": solicitacao.destino,
            "data_inicio": solicitacao.data_inicio,
            "data_fim": solicitacao.data_fim,
            "num_viajantes": solicitacao.num_viajantes,
        }
    motor.dispose()
    return dados


def _salvar_roteiros(solicitacao_id: str, roteiros: dict) -> None:
    """
    Persiste os 3 roteiros (e seus voos, hospedagens e atividades) no banco.

    `sessao.flush()` após adicionar o Roteiro garante que o `roteiro.id` é gerado
    antes de criar os Voos/Hospedagens que dependem desse ID como FK.

    Todos os níveis (economico, conforto, premium) são salvos em uma única transação.
    """
    import sqlalchemy as sa
    from sqlalchemy.orm import Session
    from viagens.modelos import Atividade, Hospedagem, NivelRoteiro, Roteiro, Voo

    url_sincrona = configuracoes.database_url.replace("+asyncpg", "+psycopg2", 1)
    motor = sa.create_engine(url_sincrona)

    with Session(motor) as sessao:
        for nivel, dados in roteiros.items():
            roteiro = Roteiro(
                solicitacao_id=uuid.UUID(solicitacao_id),
                nivel=NivelRoteiro(nivel),
                custo_total_estimado=dados.get("custo_total"),
                resumo=dados.get("resumo"),
            )
            sessao.add(roteiro)
            sessao.flush()  # necessário para obter roteiro.id antes de criar filhos

            for voo_dados in dados.get("voos", []):
                if voo_dados:
                    sessao.add(Voo(
                        roteiro_id=roteiro.id,
                        companhia=voo_dados.get("companhia", ""),
                        partida=voo_dados.get("partida"),
                        chegada=voo_dados.get("chegada"),
                        preco=voo_dados.get("preco", 0),
                        link_reserva=voo_dados.get("link_reserva"),
                    ))

            for hotel_dados in dados.get("hospedagens", []):
                if hotel_dados:
                    sessao.add(Hospedagem(
                        roteiro_id=roteiro.id,
                        nome=hotel_dados.get("nome", ""),
                        tipo=hotel_dados.get("tipo"),
                        preco_por_noite=hotel_dados.get("preco_por_noite", 0),
                        avaliacao=hotel_dados.get("avaliacao"),
                        link_reserva=hotel_dados.get("link_reserva"),
                    ))

            for ativ_dados in dados.get("atividades", []):
                if ativ_dados:
                    sessao.add(Atividade(
                        roteiro_id=roteiro.id,
                        nome=ativ_dados.get("nome", ""),
                        dia=ativ_dados.get("dia", 1),
                        horario=ativ_dados.get("horario"),
                        descricao=ativ_dados.get("descricao"),
                        custo_estimado=ativ_dados.get("custo_estimado"),
                        latitude=ativ_dados.get("latitude"),
                        longitude=ativ_dados.get("longitude"),
                    ))

        sessao.commit()
    motor.dispose()


def _atualizar_status(solicitacao_id: str, status: str) -> None:
    """Atualiza o campo `status` da solicitação. Chamado no início e fim da task."""
    import sqlalchemy as sa
    from sqlalchemy.orm import Session
    from viagens.modelos import SolicitacaoViagem, StatusSolicitacao

    url_sincrona = configuracoes.database_url.replace("+asyncpg", "+psycopg2", 1)
    motor = sa.create_engine(url_sincrona)
    with Session(motor) as sessao:
        solicitacao = sessao.get(SolicitacaoViagem, uuid.UUID(solicitacao_id))
        if solicitacao:
            solicitacao.status = StatusSolicitacao(status)
            sessao.commit()
    motor.dispose()


@app_celery.task(bind=True, name="tarefas.gerar_roteiro")
def gerar_roteiro(self, solicitacao_id: str) -> dict:
    """
    Task principal — ponto de entrada chamado pelo Celery worker.

    bind=True: `self` referencia a instância da task, necessário para self.retry()
    max_retries=0: não re-tenta automaticamente em caso de erro — o status "falhou"
    é suficiente para o usuário saber que precisa tentar novamente.

    ContextoExecucao: context manager que mede duração, estima tokens/custo
    e persiste um log no banco para cada agente (tabela logs_execucao_agente).
    """
    canal = f"progresso:{solicitacao_id}"
    logger.info(f"Iniciando geração | solicitacao={solicitacao_id}")

    try:
        _atualizar_status(solicitacao_id, "processando")
        dados = _carregar_solicitacao(solicitacao_id)

        origem = dados["origem"]
        iata_origem = dados["iata_origem"]
        iata = dados["iata_destino"]
        destino = dados["destino"]
        data_inicio = dados["data_inicio"]
        data_fim = dados["data_fim"]
        num_viajantes = dados["num_viajantes"]
        num_dias = (data_fim - data_inicio).days

        logger.info(f"{origem}({iata_origem})→{destino} | {data_inicio}→{data_fim} ({num_dias} dias) | {num_viajantes} viajante(s)")

        # ── Agente 1: Voos (OpenAI GPT-4o-mini) ──────────────────────────────
        _publicar_evento(canal, {"agente": "voos", "status": "iniciando"})
        from agentes.agente_voos import executar_agente_voos

        with ContextoExecucao(
            solicitacao_id, "voos", "openai/gpt-4o-mini",
            f"{iata_origem}→{iata} {data_inicio} {num_viajantes}pax"
        ) as ctx_voos:
            voos, usage_voos = executar_agente_voos(
                iata_origem=iata_origem,
                iata_destino=iata,
                data_ida=data_inicio.strftime("%Y-%m-%d"),
                num_viajantes=num_viajantes,
                destino=destino,
            )
            ctx_voos.registrar_saida(
                json.dumps(voos)[:2000],
                fonte="amadeus" if configuracoes.amadeus_client_id else "llm_gerado",
                tokens_entrada=usage_voos["tokens_entrada"],
                tokens_saida=usage_voos["tokens_saida"],
            )

        _publicar_evento(canal, {"agente": "voos", "status": "concluido"})

        # ── Agente 2: Hotéis (OpenAI GPT-4o-mini) ────────────────────────────
        _publicar_evento(canal, {"agente": "hoteis", "status": "iniciando"})
        from agentes.agente_hoteis import executar_agente_hoteis

        with ContextoExecucao(
            solicitacao_id, "hoteis", "openai/gpt-4o-mini",
            f"{destino} {data_inicio}→{data_fim}"
        ) as ctx_hoteis:
            hoteis, usage_hoteis = executar_agente_hoteis(
                iata_destino=iata,
                data_checkin=data_inicio.strftime("%Y-%m-%d"),
                data_checkout=data_fim.strftime("%Y-%m-%d"),
                destino=destino,
            )
            ctx_hoteis.registrar_saida(
                json.dumps(hoteis)[:2000],
                fonte="amadeus" if configuracoes.amadeus_client_id else "llm_gerado",
                tokens_entrada=usage_hoteis["tokens_entrada"],
                tokens_saida=usage_hoteis["tokens_saida"],
            )

        _publicar_evento(canal, {"agente": "hoteis", "status": "concluido"})

        # ── Agente 3: Atividades (OpenAI GPT-4.1-mini) ───────────────────────
        _publicar_evento(canal, {"agente": "atividades", "status": "iniciando"})
        from agentes.agente_atividades import executar_agente_atividades

        with ContextoExecucao(
            solicitacao_id, "atividades", "openai/gpt-4.1-mini",
            f"{destino} {num_dias} dias"
        ) as ctx_ativ:
            atividades, usage_ativ = executar_agente_atividades(
                destino=destino,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
            ctx_ativ.registrar_saida(
                json.dumps(atividades.get("conforto", [])[:3])[:2000],
                fonte="google_places" if configuracoes.google_places_api_key else "llm_gerado",
                tokens_entrada=usage_ativ["tokens_entrada"],
                tokens_saida=usage_ativ["tokens_saida"],
            )

        _publicar_evento(canal, {"agente": "atividades", "status": "concluido"})

        # ── Agente 4: Arquiteto de Roteiros (OpenAI GPT-4.1-mini) ────────────
        _publicar_evento(canal, {"agente": "arquiteto", "status": "iniciando"})
        from agentes.arquiteto_roteiros import executar_arquiteto

        with ContextoExecucao(
            solicitacao_id, "arquiteto", "openai/gpt-4.1-mini",
            f"{destino} {num_dias} dias — síntese"
        ) as ctx_arq:
            roteiros, usage_arq = executar_arquiteto(
                destino=destino,
                num_dias=num_dias,
                voos=voos,
                hoteis=hoteis,
                atividades=atividades,
            )
            ctx_arq.registrar_saida(
                json.dumps({k: v.get("resumo", "") for k, v in roteiros.items()})[:2000],
                tokens_entrada=usage_arq["tokens_entrada"],
                tokens_saida=usage_arq["tokens_saida"],
            )

        _publicar_evento(canal, {"agente": "arquiteto", "status": "concluido"})

        # ── Finalizar ─────────────────────────────────────────────────────────
        _salvar_roteiros(solicitacao_id, roteiros)
        _atualizar_status(solicitacao_id, "concluido")
        # Evento "finalizado" dispara o redirecionamento no frontend
        _publicar_evento(canal, {"tipo": "finalizado", "solicitacao_id": solicitacao_id})

        logger.info(f"Geração concluída | solicitacao={solicitacao_id}")
        return {"status": "concluido", "solicitacao_id": solicitacao_id}

    except Exception as exc:
        logger.error(f"Geração falhou | solicitacao={solicitacao_id} | erro={exc}", exc_info=True)
        _atualizar_status(solicitacao_id, "falhou")
        _publicar_evento(canal, {"tipo": "erro", "mensagem": str(exc)})
        raise self.retry(exc=exc, max_retries=0)
