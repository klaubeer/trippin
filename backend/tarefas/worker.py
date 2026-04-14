"""
Configuração do Celery — sistema de filas para processamento assíncrono.

Por que Celery?
- Os 4 agentes IA levam de 1 a 5 minutos para executar — tempo inaceitável para um request HTTP
- Celery permite disparar a execução em background e retornar ao cliente imediatamente
- O frontend acompanha o progresso via SSE enquanto o worker processa em paralelo

Por que Redis como broker (e não RabbitMQ)?
- Redis já é usado para Pub/Sub do SSE — reduz o número de serviços no Docker
- Para o volume do Trippin', Redis é mais que suficiente como broker de tasks
- RabbitMQ seria mais robusto para alto volume com múltiplas filas, mas over-engineering aqui

Configuração:
- broker = Redis: onde as tasks ficam enfileiradas
- backend = Redis: onde os resultados das tasks são armazenados
- task_soft_time_limit: lança SoftTimeLimitExceeded após N segundos (configurável via .env)
- task_time_limit: mata o processo após soft_limit + 30s se a task não encerrar
"""
from celery import Celery

from config import configuracoes

app_celery = Celery(
    "trippin",
    broker=configuracoes.redis_url,
    backend=configuracoes.redis_url,
    include=["tarefas.gerar_roteiro"],  # módulos que contêm tasks — necessário para auto-discover
)

app_celery.conf.update(
    task_serializer="json",        # serialização JSON em vez de pickle — mais seguro
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",  # para logging com horário correto no Brasil
    enable_utc=True,               # armazena timestamps em UTC internamente
    task_soft_time_limit=configuracoes.timeout_agentes_segundos,
    task_time_limit=configuracoes.timeout_agentes_segundos + 30,
)
