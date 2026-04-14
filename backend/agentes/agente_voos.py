"""
Agente de Voos — OpenAI GPT-4o-mini + Amadeus Sandbox

Por que GPT-4o-mini para voos?
- Confiável, rápido e sem limitações de rate limit problemáticas dos tiers gratuitos
- Excelente em tarefas estruturadas de formatação de JSON
- Custo baixo: ~$0.15/1M tokens de input, $0.60/1M tokens de output
- Tarefa mais estruturada dos 4 agentes — não exige raciocínio complexo

Por que CrewAI?
- Abstrai a orquestração de LLM + tool use em uma API simples
- Agent/Task/Crew separa responsabilidades: quem executa, o que executa, como executa
- Suporta múltiplos providers (Groq, Gemini, OpenAI, Anthropic) via mesmo interface

Estratégia de fallback:
- Se Amadeus não está configurado → LLM gera dados plausíveis com conhecimento próprio
- Se Amadeus retorna vazio → LLM preenche com estimativas de mercado
- Se a chamada falha → LLM tenta gerar dados, se JSON inválido → fallback hardcoded
"""
import json

import httpx
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from config import configuracoes

AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_VOOS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def _obter_token_amadeus() -> str:
    """
    Obtém um token de acesso OAuth2 da API Amadeus.
    O token expira em 30 minutos — obtido a cada chamada para simplicidade
    (em produção, seria cacheado no Redis).
    """
    with httpx.Client() as cliente:
        resposta = cliente.post(
            AMADEUS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": configuracoes.amadeus_client_id,
                "client_secret": configuracoes.amadeus_client_secret,
            },
            timeout=10,
        )
        resposta.raise_for_status()
        return resposta.json()["access_token"]


def criar_ferramenta_voos(iata_origem: str, iata_destino: str, data_ida: str, num_viajantes: int):
    """
    Cria a tool de busca de voos com os parâmetros da viagem fechados no closure.

    Por que closure em vez de parâmetros diretos?
    - CrewAI tools são funções com assinatura fixa (apenas `consulta: str`)
    - O closure captura os parâmetros da viagem sem precisar mudá-los no prompt
    """

    @tool("Buscar Voos Amadeus")
    def buscar_voos(consulta: str) -> str:
        """
        Busca voos disponíveis na API Amadeus para a rota e data informadas.
        Retorna lista de opções ou instrução para gerar dados com o LLM.

        Args:
            consulta: Descrição do que buscar (ex: 'voos para Paris em julho')
        """
        # Modo demo ou sem credenciais → instrui o LLM a gerar dados plausíveis
        if configuracoes.modo_demo or not configuracoes.amadeus_client_id:
            return (
                "API Amadeus não configurada. "
                "Use seu conhecimento para gerar 5 opções realistas de voo "
                f"de {iata_origem} para {iata_destino} na data {data_ida} "
                f"para {num_viajantes} viajante(s). "
                "Baseie os preços em valores reais de mercado para essa rota."
            )

        try:
            token = _obter_token_amadeus()
            with httpx.Client() as cliente:
                resposta = cliente.get(
                    AMADEUS_VOOS_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "originLocationCode": iata_origem,
                        "destinationLocationCode": iata_destino,
                        "departureDate": data_ida,
                        "adults": num_viajantes,
                        "currencyCode": "BRL",
                        "max": 10,
                    },
                    timeout=15,
                )
                resposta.raise_for_status()
                voos_amadeus = resposta.json().get("data", [])

            if not voos_amadeus:
                return (
                    "Nenhum voo encontrado na API Amadeus para esta rota. "
                    "Use seu conhecimento para gerar 5 opções realistas de voo "
                    f"de {iata_origem} para {iata_destino} na data {data_ida}."
                )

            # Normaliza a estrutura da resposta Amadeus para o formato esperado pelo agente
            voos = [
                {
                    "companhia": v["validatingAirlineCodes"][0] if v.get("validatingAirlineCodes") else "Desconhecida",
                    "partida": v["itineraries"][0]["segments"][0]["departure"]["at"],
                    "chegada": v["itineraries"][0]["segments"][-1]["arrival"]["at"],
                    "preco": float(v["price"]["total"]),
                    "link_reserva": None,  # Sandbox não fornece links reais
                }
                for v in voos_amadeus
            ]
            return json.dumps(voos, ensure_ascii=False)

        except Exception as exc:
            return (
                f"Erro ao acessar Amadeus: {exc}. "
                "Use seu conhecimento para gerar 5 opções realistas de voo "
                f"de {iata_origem} para {iata_destino} na data {data_ida}."
            )

    return buscar_voos


def executar_agente_voos(
    iata_origem: str, iata_destino: str, data_ida: str, num_viajantes: int, destino: str
) -> tuple[dict, dict]:
    """
    Executa o agente de voos e retorna as opções nos 3 tiers (econômico, conforto, premium).

    Parsing robusto: extrai apenas o bloco JSON da resposta do LLM
    (que pode conter texto antes/depois do JSON).
    Se o JSON for inválido, retorna um fallback hardcoded com valores plausíveis.
    """
    llm = LLM(
        model="openai/gpt-4o-mini",
        api_key=configuracoes.openai_api_key or "sem-chave",
        temperature=0.2,
        max_tokens=800,
        timeout=60,
    )

    ferramenta_voos = criar_ferramenta_voos(iata_origem, iata_destino, data_ida, num_viajantes)

    agente = Agent(
        role="Flight Expert",
        goal=f"Find flights {iata_origem}→{iata_destino} in 3 tiers: economy, comfort, premium.",
        backstory=(
            "Expert in airfare with deep knowledge of routes, airlines, prices, and schedules. "
            "When API unavailable, generates realistic market-accurate flight options."
        ),
        tools=[ferramenta_voos],
        llm=llm,
        verbose=True,
    )

    tarefa = Task(
        description=(
            f"Use 'Buscar Voos Amadeus' for {iata_origem}→{iata_destino} on {data_ida}, "
            f"{num_viajantes} passenger(s). If tool says to generate data, create realistic options. "
            "Return ONLY valid JSON:\n"
            '{"economico":{"companhia":"","partida":"YYYY-MM-DDTHH:MM:SS","chegada":"YYYY-MM-DDTHH:MM:SS","preco":0.0,"link_reserva":null},'
            '"conforto":{...},"premium":{...}}'
        ),
        expected_output="JSON with keys economico, conforto, premium — each with companhia, partida, chegada, preco, link_reserva.",
        agent=agente,
    )

    crew = Crew(agents=[agente], tasks=[tarefa], process=Process.sequential, verbose=False)
    resultado = crew.kickoff()

    # Tokens reais reportados pela API (mais preciso que heurística de chars)
    uso = crew.usage_metrics
    usage = {
        "tokens_entrada": getattr(uso, "prompt_tokens", 0) or 0,
        "tokens_saida": getattr(uso, "completion_tokens", 0) or 0,
    }

    # Extrai apenas o bloco JSON — LLMs frequentemente adicionam texto antes/depois
    texto = resultado.raw.strip()
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1

    try:
        return json.loads(texto[inicio:fim]), usage
    except (json.JSONDecodeError, ValueError):
        # Fallback com valores plausíveis para não quebrar o fluxo
        return {
            "economico": {"companhia": "GOL", "partida": f"{data_ida}T14:00:00", "chegada": f"{data_ida}T20:00:00", "preco": 2200.0, "link_reserva": None},
            "conforto":  {"companhia": "LATAM", "partida": f"{data_ida}T22:00:00", "chegada": f"{data_ida}T08:00:00", "preco": 3800.0, "link_reserva": None},
            "premium":   {"companhia": "Air France", "partida": f"{data_ida}T23:30:00", "chegada": f"{data_ida}T16:00:00", "preco": 8500.0, "link_reserva": None},
        }, usage
