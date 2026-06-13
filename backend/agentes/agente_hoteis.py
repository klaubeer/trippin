"""
Agente de Hotéis — OpenAI GPT-4o-mini + Amadeus Hotel Search

Por que GPT-4o-mini para hotéis?
- Confiável e sem problemas de rate limit de tier gratuito
- Excelente em tarefas de formatação de dados estruturados (JSON)
- Mesmo modelo do agente de voos — simplicidade operacional

Estratégia de fallback (mesma do agente de voos):
- Sem Amadeus → LLM gera nomes/preços plausíveis
- JSON inválido → fallback hardcoded com redes hoteleiras conhecidas
"""
import json

import httpx
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from config import configuracoes

AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_HOTEIS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"


def _obter_token_amadeus() -> str:
    """
    Obtém token OAuth2 da Amadeus para autenticar chamadas à API de hotéis.
    Mesmo endpoint de auth do agente de voos — credenciais compartilhadas.
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


def criar_ferramenta_hoteis(iata_destino: str, data_checkin: str, data_checkout: str):
    """
    Cria a tool de busca de hotéis com os parâmetros fechados no closure.
    Mesmo padrão de closure do agente de voos.
    """

    @tool("Buscar Hotéis Amadeus")
    def buscar_hoteis(consulta: str) -> str:
        """
        Busca hotéis disponíveis na API Amadeus para o destino da viagem.
        Retorna lista de hotéis ou solicita que você gere os dados com seu conhecimento.

        Args:
            consulta: Descrição do que buscar (ex: 'hotéis em Paris para julho')
        """
        if configuracoes.modo_demo or not configuracoes.amadeus_client_id:
            return (
                f"Sem API externa — use seu conhecimento real do destino ({iata_destino}), "
                f"check-in {data_checkin}, check-out {data_checkout}. "
                "Recomende hospedagens REAIS e nomeadas que você conhece, uma por tier, cada "
                "uma no bairro certo para aquele perfil. Prefira lugares consagrados a inventar "
                "nomes. Preços realistas em BRL/noite e avaliação coerente. Siga o briefing da tarefa."
            )

        try:
            token = _obter_token_amadeus()
            with httpx.Client() as cliente:
                resposta = cliente.get(
                    AMADEUS_HOTEIS_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "cityCode": iata_destino,
                        "checkInDate": data_checkin,
                        "checkOutDate": data_checkout,
                        "adults": 1,
                        "currency": "BRL",
                        "max": 10,
                    },
                    timeout=15,
                )
                resposta.raise_for_status()
                hoteis_amadeus = resposta.json().get("data", [])

            if not hoteis_amadeus:
                return (
                    "Nenhum hotel encontrado na API Amadeus. "
                    "Use seu conhecimento para criar 4 opções plausíveis de hospedagem "
                    f"em {iata_destino}, com preços realistas em BRL."
                )

            # Normaliza a estrutura da resposta Amadeus
            hoteis = [
                {
                    "nome": h.get("hotel", {}).get("name", "Hotel"),
                    "tipo": "Hotel",
                    "preco_por_noite": float(h["offers"][0]["price"]["total"]) if h.get("offers") else 0,
                    "avaliacao": float(h.get("hotel", {}).get("rating", 0)) or None,
                    "link_reserva": None,
                }
                for h in hoteis_amadeus
            ]
            return json.dumps(hoteis, ensure_ascii=False)

        except Exception as exc:
            return (
                f"Erro ao acessar Amadeus: {exc}. "
                "Use seu conhecimento para criar 4 opções plausíveis de hospedagem "
                f"em {iata_destino} com preços realistas em BRL."
            )

    return buscar_hoteis


def executar_agente_hoteis(
    iata_destino: str, data_checkin: str, data_checkout: str, destino: str
) -> tuple[dict, dict]:
    """
    Executa o agente de hotéis e retorna as opções nos 3 tiers.
    Fallback usa redes hoteleiras internacionais conhecidas (Ibis, Mercure, Sofitel).
    """
    llm = LLM(
        model="openai/gpt-4o-mini",
        api_key=configuracoes.openai_api_key or "sem-chave",
        temperature=0.45,  # alguma personalidade na escolha, mantendo JSON estável
    )

    ferramenta_hoteis = criar_ferramenta_hoteis(iata_destino, data_checkin, data_checkout)

    agente = Agent(
        role="Consultora de hospedagem com olhar de quem dorme na cidade",
        goal=(
            f"Recomendar UMA hospedagem por tier em {destino} (econômico, conforto, premium), "
            "cada uma no bairro certo para aquele perfil, com uma razão clara de escolha."
        ),
        backstory=(
            f"Você conhece {destino} cama a cama: sabe quais bairros valem por localização, vibe e "
            "segurança, e quais hotéis entregam o que prometem. Não recomenda por estrelas no site — "
            "recomenda pelo que a estadia de fato proporciona: acordar a dois passos do que importa, "
            "um terraço com a vista certa, um café da manhã que vale a pena. Cada tier merece uma "
            "decisão de bairro e de caráter diferente, não o mesmo hotel com diária maior."
        ),
        tools=[ferramenta_hoteis],
        llm=llm,
        verbose=True,
    )

    tarefa = Task(
        description=(
            f"Recomende hospedagem em {destino} ({iata_destino}), de {data_checkin} a {data_checkout}. "
            "Use a ferramenta 'Buscar Hotéis Amadeus' como apoio; a curadoria é sua. "
            "Prefira lugares REAIS e nomeados que você conhece.\n\n"

            "Cada tier tem uma LÓGICA DE ESCOLHA diferente (não é o mesmo hotel mais caro):\n"
            "• econômico — melhor custo-benefício num bairro autêntico, seguro e bem conectado "
            "(hostel bom, guesthouse ou 2–3★). O valor está na localização e na vibe, não no luxo.\n"
            "• conforto — 3–4★ ou boutique bem localizado, a pé das principais atrações, com bom "
            "café da manhã e quarto confortável. O 'lugar certo' para a maioria das pessoas.\n"
            "• premium — hotel-destino: ícone, design ou heritage com história, vista, spa ou bar "
            "célebre. A hospedagem vira parte da experiência da viagem.\n\n"

            "Campos: 'nome' = nome real do hotel. 'tipo' = uma linha editorial CURTA (máx ~80 "
            "caracteres) com categoria + bairro + 1 diferencial — ex.: 'Boutique no Bairro Alto — "
            "terraço com vista'. 'preco_por_noite' em BRL realista para a cidade e o tier. "
            "'avaliacao' coerente (3.0–5.0).\n"
            "Retorne APENAS JSON válido, sem texto fora dele:\n"
            '{"economico": {"nome": "", "tipo": "", "preco_por_noite": 0.0, "avaliacao": 0.0, "link_reserva": null}, '
            '"conforto": {...}, "premium": {...}}'
        ),
        expected_output=(
            "JSON com 3 chaves (economico, conforto, premium), cada uma com nome real, tipo "
            "(linha editorial curta com bairro + diferencial), preco_por_noite em BRL, avaliacao e link_reserva."
        ),
        agent=agente,
    )

    crew = Crew(agents=[agente], tasks=[tarefa], process=Process.sequential, verbose=False)
    resultado = crew.kickoff()

    uso = crew.usage_metrics
    usage = {
        "tokens_entrada": getattr(uso, "prompt_tokens", 0) or 0,
        "tokens_saida": getattr(uso, "completion_tokens", 0) or 0,
    }

    texto = resultado.raw.strip()
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1

    try:
        return json.loads(texto[inicio:fim]), usage
    except (json.JSONDecodeError, ValueError):
        return {
            "economico": {"nome": f"Ibis {destino} Centre", "tipo": "Econômico", "preco_por_noite": 150.0, "avaliacao": 3.7, "link_reserva": None},
            "conforto":  {"nome": f"Mercure {destino} Opera", "tipo": "Superior", "preco_por_noite": 380.0, "avaliacao": 4.2, "link_reserva": None},
            "premium":   {"nome": f"Sofitel {destino} Grand", "tipo": "Luxo", "preco_por_noite": 1100.0, "avaliacao": 4.8, "link_reserva": None},
        }, usage
