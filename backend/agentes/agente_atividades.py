"""
Agente de Atividades — OpenAI GPT-4.1-mini + Google Places API

Por que GPT-4.1-mini para atividades?
- Modelo mais capaz da família mini — melhor qualidade para roteiros culturais detalhados
- Excelente em gerar conteúdo contextualizado com horários, custos e descrições ricas
- Lida bem com roteiros estruturados dia a dia para múltiplos dias

Por que Google Places para os dados base?
- Fornece coordenadas geográficas reais — essenciais para o mapa Leaflet
- Retorna avaliações, endereços e categorias que o LLM enriquece na descrição
- Fallback com coordenadas aproximadas quando a API não está configurada

Nota sobre o mock de atividades (_dados_mock_atividades):
- Usado apenas quando o LLM retorna JSON inválido (situação rara)
- Usa coordenadas de Paris como placeholder — aceitável para demo
"""
import json
from datetime import date

import httpx
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from config import configuracoes

GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# Nomes dos meses em pt-BR — usados para dar ao agente o contexto de sazonalidade
# (clima, alta/baixa temporada, festivais) sem depender de locale do servidor.
MESES_PT = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _dados_mock_atividades(destino: str, num_dias: int) -> dict[str, list[dict]]:
    """
    Dados de fallback quando o JSON retornado pelo LLM é inválido.
    Retorna 3 tiers (economico, conforto, premium) com atividades diferenciadas.
    """
    base_eco = [
        {"nome": f"Parque Central de {destino}", "descricao": "Área verde no coração da cidade, ideal para caminhadas gratuitas.", "custo_estimado": 0.0, "latitude": 48.8650, "longitude": 2.3370},
        {"nome": f"Bairro Histórico de {destino}", "descricao": "Passeio pelas ruas do centro histórico — gratuito.", "custo_estimado": 0.0, "latitude": 48.8530, "longitude": 2.3490},
        {"nome": f"Museu Municipal de {destino}", "descricao": "Museu público com entrada gratuita ou de baixo custo.", "custo_estimado": 20.0, "latitude": 48.8566, "longitude": 2.3522},
        {"nome": f"Mercado Local de {destino}", "descricao": "Mercado popular com lanches e produtos típicos baratos.", "custo_estimado": 30.0, "latitude": 48.8640, "longitude": 2.3360},
    ]
    base_conf = [
        {"nome": f"Museu Principal de {destino}", "descricao": "Principal museu da cidade com acervo histórico e cultural.", "custo_estimado": 60.0, "latitude": 48.8566, "longitude": 2.3522},
        {"nome": f"Passeio Guiado por {destino}", "descricao": "Tour guiado pelos principais pontos turísticos.", "custo_estimado": 120.0, "latitude": 48.8584, "longitude": 2.2945},
        {"nome": f"Restaurante Tradicional de {destino}", "descricao": "Culinária local autêntica com ambiente confortável.", "custo_estimado": 150.0, "latitude": 48.8700, "longitude": 2.3300},
        {"nome": f"Mirante de {destino}", "descricao": "Vista panorâmica da cidade com entrada paga.", "custo_estimado": 50.0, "latitude": 48.8640, "longitude": 2.3370},
    ]
    base_prem = [
        {"nome": f"Tour VIP por {destino}", "descricao": "Tour exclusivo com guia particular e acesso prioritário.", "custo_estimado": 450.0, "latitude": 48.8584, "longitude": 2.2945},
        {"nome": f"Restaurante Gourmet de {destino}", "descricao": "Jantar fine dining com culinária de alta gastronomia.", "custo_estimado": 600.0, "latitude": 48.8700, "longitude": 2.3300},
        {"nome": f"Experiência Cultural Exclusiva em {destino}", "descricao": "Visita privada a acervo fechado ao público geral.", "custo_estimado": 300.0, "latitude": 48.8566, "longitude": 2.3522},
        {"nome": f"Spa e Bem-Estar em {destino}", "descricao": "Sessão de spa premium no melhor hotel da cidade.", "custo_estimado": 350.0, "latitude": 48.8650, "longitude": 2.3370},
    ]
    result: dict[str, list[dict]] = {"economico": [], "conforto": [], "premium": []}
    for base, tier in [(base_eco, "economico"), (base_conf, "conforto"), (base_prem, "premium")]:
        for dia in range(1, num_dias + 1):
            result[tier].append({**base[(dia - 1) % len(base)], "dia": dia, "horario": "09:00:00"})
            result[tier].append({**base[dia % len(base)], "dia": dia, "horario": "15:00:00"})
    return result


def criar_ferramenta_atividades(destino: str):
    """Cria a tool do Google Places com o destino fixado no closure."""

    @tool("Buscar Atividades Google Places")
    def buscar_atividades(tipo_busca: str) -> str:
        """
        Busca atrações turísticas, restaurantes e atividades no destino via Google Places API.
        Retorna lista de lugares com nome, descrição, avaliação e coordenadas.

        Args:
            tipo_busca: Tipo de lugar a buscar (ex: 'pontos turísticos', 'restaurantes', 'museus')
        """
        if configuracoes.modo_demo or not configuracoes.google_places_api_key:
            return (
                f"Sem API externa — use seu conhecimento real de {destino}. "
                "Liste lugares ESPECÍFICOS e nomeados (atrações, bairros, miradouros, "
                "restaurantes, bares, mercados, experiências), não categorias genéricas. "
                "Prefira lugares que você realmente conhece a inventar nomes. "
                "Para cada um: nome real, por que vale a pena, custo em BRL e "
                "coordenadas (lat/lng) precisas. Siga à risca o briefing da tarefa."
            )

        try:
            with httpx.Client() as cliente:
                resposta = cliente.get(
                    GOOGLE_PLACES_URL,
                    params={
                        "query": f"{tipo_busca} em {destino}",
                        "key": configuracoes.google_places_api_key,
                        "language": "pt-BR",
                    },
                    timeout=10,
                )
                resposta.raise_for_status()
                lugares = resposta.json().get("results", [])

            # Extrai apenas os campos relevantes para o agente
            resultado = [
                {
                    "nome": l.get("name", ""),
                    "descricao": l.get("formatted_address", ""),
                    "latitude": l.get("geometry", {}).get("location", {}).get("lat"),
                    "longitude": l.get("geometry", {}).get("location", {}).get("lng"),
                    "avaliacao": l.get("rating"),
                }
                for l in lugares[:8]  # limita a 8 resultados por busca
            ]
            return json.dumps(resultado, ensure_ascii=False)

        except Exception as exc:
            return (
                f"Erro ao acessar Google Places: {exc}. "
                f"Use seu conhecimento para listar atrações reais de {destino} "
                "com coordenadas aproximadas e preços em BRL."
            )

    return buscar_atividades


def executar_agente_atividades(
    destino: str, data_inicio: date, data_fim: date
) -> tuple[dict[str, list[dict]], dict]:
    """
    Executa o agente de atividades e retorna atividades separadas por tier.

    Retorna um dict com 3 chaves (economico, conforto, premium), cada uma com
    uma lista de atividades com 2 itens por dia (manhã e tarde).

    As atividades diferem por tier:
    - econômico: atrações gratuitas e de baixo custo (R$0–80), comida de rua
    - conforto: museus, passeios guiados e restaurantes tradicionais (R$50–200)
    - premium: tours VIP, fine dining e experiências exclusivas (R$200+)

    Parsing: extrai o bloco JSON da resposta (delimitado por { }).
    Fallback: _dados_mock_atividades se o JSON for inválido.
    """
    num_dias = (data_fim - data_inicio).days
    mes_pt = MESES_PT[data_inicio.month]
    periodo = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"

    llm = LLM(
        model="openai/gpt-4.1-mini",
        api_key=configuracoes.openai_api_key or "sem-chave",
        temperature=0.6,  # mais alto: queremos personalidade e opinião, não lista neutra
        max_tokens=6000,
    )

    ferramenta_atividades = criar_ferramenta_atividades(destino)

    agente = Agent(
        role="Curador de viagens local e opinativo",
        goal=(
            f"Montar 3 roteiros de {num_dias} dias em {destino} (econômico, conforto, premium) "
            "que pareçam escritos por um amigo que mora lá: lugares nomeados, escolhas com "
            "opinião e justificativa, ritmo realista e lógica geográfica."
        ),
        backstory=(
            f"Você morou em {destino} e conhece a cidade pela vivência, não por guia de banca. "
            "Sabe qual fila não vale a pena, qual mirante render no fim de tarde, onde os locais "
            "comem de verdade e qual 'atração imperdível' é só armadilha de turista. Você tem GOSTO "
            "e OPINIÃO — recomenda como quem indica para um amigo querido, dizendo o porquê de cada "
            "escolha, o que pedir, o melhor horário e o detalhe que ninguém conta. Você odeia roteiro "
            "genérico e desfile de obviedades."
        ),
        tools=[ferramenta_atividades],
        llm=llm,
        verbose=True,
    )

    tarefa = Task(
        description=(
            f"Monte 3 roteiros de {num_dias} dias em {destino}, viagem de {periodo} "
            f"(mês: {mes_pt}). Use a ferramenta 'Buscar Atividades Google Places' como apoio, "
            "mas a curadoria, a voz e as escolhas são suas.\n\n"

            "=== BARRA DE QUALIDADE (inegociável) ===\n"
            "1. ESPECÍFICO: sempre o nome próprio do lugar (restaurante, bar, museu, rua, mirante, "
            "mercado, bairro). NUNCA 'um bom restaurante local' ou 'museu da cidade'. Prefira lugares "
            "reais que você conhece; só invente se não houver alternativa, e mesmo assim que seja crível.\n"
            "2. O PORQUÊ: cada 'descricao' (2–3 frases) diz por que VOCÊ escolheu aquilo — o que ver/pedir, "
            "o melhor momento, um detalhe não óbvio ou dica de quem é de casa. Tom de amigo, com opinião.\n"
            "3. SEM ARMADILHA DE TURISTA: evite o óbvio caro e fraco; quando citar um clássico, diga como "
            "fazê-lo bem (horário, entrada alternativa) ou ofereça a versão que os locais preferem.\n"
            "4. LÓGICA GEOGRÁFICA: agrupe as atividades de um mesmo dia no mesmo bairro/região para "
            "minimizar deslocamento; encadeie os dias percorrendo a cidade de forma coerente. As "
            "coordenadas (lat/lng) precisam ser REAIS e precisas — elas vão num mapa.\n"
            "5. RITMO REALISTA: 2 blocos por dia (manhã e tarde) e, em dias-chave, um 3º bloco à noite "
            "(jantar/bar/vida noturna). Horários plausíveis. Não empilhe atrações cansativas. Inclua "
            "comida de verdade ao longo da viagem. Dia 1 = chegada: comece leve e perto da hospedagem, "
            "feche com um bom jantar. Último dia: nada de correria, algo tranquilo pensando na partida.\n"
            f"6. SAZONALIDADE: é {mes_pt}. Considere clima, alta/baixa temporada, festivais/feriados e "
            "o que evitar nesse período. Se algo estiver fora de época ou fechado, não recomende.\n\n"

            "=== OS 3 TIERS TÊM LÓGICA DE ESCOLHA DIFERENTE (não é o mesmo roteiro com preço trocado) ===\n"
            "• econômico (custo_estimado R$0–80) — olhar de quem viaja esperto: o melhor de graça ou "
            "barato. Bairros a pé, mirantes, mercados, comida de rua e botecos, parques, dias de museu "
            "grátis, transporte público. Prioriza autenticidade e descoberta sobre conforto.\n"
            "• conforto (R$50–250) — os ícones bem feitos, sem turistar mal: principais atrações com "
            "ingresso/sem fila quando vale, bairros charmosos, restaurantes queridos de preço médio, "
            "um ou outro tour bom. Equilíbrio entre ver o essencial e curtir com calma.\n"
            "• premium (R$200–1500) — curadoria de concierge: o que dinheiro e bom gosto abrem. Guias "
            "privativos, mesas disputadas/alta gastronomia, acesso especial (após o horário, nos "
            "bastidores), experiências únicas (barco privativo, chef's table, day trip com motorista). "
            "Exclusividade e história, não só 'a versão cara do mesmo passeio'.\n\n"

            "Custos em BRL (estimados, por pessoa). Retorne APENAS JSON válido, sem texto fora dele:\n"
            '{"economico": [{"nome": "", "dia": 1, "horario": "09:00:00", "descricao": "", "custo_estimado": 0.0, "latitude": 0.0, "longitude": 0.0}], '
            '"conforto": [...], "premium": [...]}'
        ),
        expected_output=(
            "JSON com 3 chaves (economico, conforto, premium), cada uma uma lista de atividades "
            f"cobrindo os {num_dias} dias, com nome próprio do lugar, descricao opinativa (o porquê), "
            "horario plausível, custo_estimado em BRL e latitude/longitude reais. Tiers com lógicas distintas."
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

    if inicio == -1 or fim == 0:
        return _dados_mock_atividades(destino, num_dias), usage

    try:
        parsed = json.loads(texto[inicio:fim])
        # Valida que as 3 chaves existem e são listas
        if all(isinstance(parsed.get(k), list) for k in ("economico", "conforto", "premium")):
            return parsed, usage
        return _dados_mock_atividades(destino, num_dias), usage
    except json.JSONDecodeError:
        return _dados_mock_atividades(destino, num_dias), usage
