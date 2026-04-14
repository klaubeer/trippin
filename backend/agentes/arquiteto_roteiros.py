"""
Arquiteto de Roteiros — OpenAI GPT-4.1-mini

Por que GPT-4.1-mini para a síntese final?
- Modelo mais capaz da família mini — melhor raciocínio para síntese complexa
- Excelente na geração de texto coeso para os resumos dos roteiros
- Ótimo em estruturas JSON complexas (combina dados de 3 agentes em 3 roteiros)

Responsabilidade deste agente:
- Recebe os outputs dos 3 agentes anteriores (voos, hotéis, atividades)
- Combina em 3 roteiros coerentes (econômico, conforto, premium)
- Escreve um resumo de 2 frases para cada roteiro
- Calcula (ou valida) o custo total estimado

A ferramenta "Consultar Dados dos Agentes" usa closure para expor os dados
dos outros agentes como se fossem uma "API interna" — o LLM consulta
o que precisa sem ter todos os dados no prompt (economiza tokens).
"""
import json
from datetime import date

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

from config import configuracoes


def _calcular_custo(voo: dict, hotel: dict, atividades: list[dict], num_dias: int) -> float:
    """
    Calcula o custo total estimado: voo + (hotel × dias) + soma das atividades.
    Usado como fallback quando o LLM não retorna o custo_total no JSON.
    """
    custo_voo = float(voo.get("preco", 0))
    custo_hotel = float(hotel.get("preco_por_noite", 0)) * num_dias
    custo_atividades = sum(float(a.get("custo_estimado") or 0) for a in atividades)
    return round(custo_voo + custo_hotel + custo_atividades, 2)


def _montar_roteiros_fallback(voos: dict, hoteis: dict, atividades: dict[str, list[dict]], num_dias: int) -> dict:
    """
    Monta os 3 roteiros sem passar pelo LLM — usado quando o JSON retornado é inválido.
    Garante que a geração não falha mesmo se o GPT-4o-mini retornar algo inesperado.
    """
    resumos = {
        "economico": "Roteiro econômico com foco em custo-benefício. Ideal para quem quer aproveitar ao máximo com orçamento controlado.",
        "conforto": "Roteiro equilibrado entre conforto e preço. Hospedagem confortável e as principais atrações da cidade.",
        "premium": "Roteiro premium com o melhor que a cidade oferece. Hotéis de luxo, voos mais confortáveis e experiências exclusivas.",
    }
    roteiros = {}
    for nivel in ("economico", "conforto", "premium"):
        voo = voos.get(nivel, {})
        hotel = hoteis.get(nivel, {})
        ativs = atividades.get(nivel, [])
        roteiros[nivel] = {
            "resumo": resumos[nivel],
            "custo_total": _calcular_custo(voo, hotel, ativs, num_dias),
            "voos": [voo] if voo else [],
            "hospedagens": [hotel] if hotel else [],
            "atividades": ativs,
        }
    return roteiros


def criar_ferramenta_dados(voos: dict, hoteis: dict, atividades: dict[str, list[dict]]):
    """
    Cria uma tool que expõe os dados dos outros agentes ao arquiteto.

    Por que uma tool em vez de colocar tudo no prompt?
    - Reduz tokens consumidos — o LLM consulta apenas o que precisa
    - Simula uma arquitetura de agentes com "memória compartilhada"
    - Demonstra uso de tools com filtragem por consulta

    Limita atividades a 10 para evitar ultrapassar o context window do modelo.
    """
    dados_consolidados = {
        "voos": voos,
        "hoteis": hoteis,
        "atividades": {k: v[:5] for k, v in atividades.items()},  # amostra por tier para o resumo
    }

    @tool("Consultar Dados dos Agentes")
    def consultar_dados(consulta: str) -> str:
        """
        Retorna os dados coletados pelos agentes de voos, hotéis e atividades.
        Use esta ferramenta para acessar as informações necessárias para montar os roteiros.

        Args:
            consulta: O que deseja consultar (ex: 'voos', 'hotéis', 'atividades', 'todos')
        """
        consulta_lower = consulta.lower()
        if "voo" in consulta_lower:
            return json.dumps({"voos": dados_consolidados["voos"]}, ensure_ascii=False)
        if "hotel" in consulta_lower or "hospedagem" in consulta_lower:
            return json.dumps({"hoteis": dados_consolidados["hoteis"]}, ensure_ascii=False)
        if "atividade" in consulta_lower:
            return json.dumps({"atividades": dados_consolidados["atividades"]}, ensure_ascii=False)
        # Retorna tudo se a consulta não for específica
        return json.dumps(dados_consolidados, ensure_ascii=False)

    return consultar_dados


def executar_arquiteto(
    destino: str,
    num_dias: int,
    voos: dict,
    hoteis: dict,
    atividades: dict[str, list[dict]],
) -> tuple[dict, dict]:
    """
    Sintetiza os dados dos 3 agentes em 3 roteiros completos.

    O LLM retorna apenas o resumo e custo_total — os dados de voos/hotéis/atividades
    são combinados localmente (mais confiável do que deixar o LLM reproduzi-los).

    Estrutura retornada:
    {
      "economico": {
        "resumo": "...",
        "custo_total": 5000.0,
        "voos": [{...}],
        "hospedagens": [{...}],
        "atividades": [{...}, ...]
      },
      "conforto": {...},
      "premium": {...}
    }
    """
    llm = LLM(
        model="openai/gpt-4.1-mini",
        api_key=configuracoes.openai_api_key or "sem-chave",
        temperature=0.3,
    )

    ferramenta_dados = criar_ferramenta_dados(voos, hoteis, atividades)

    agente = Agent(
        role="Arquiteto de Roteiros de Viagem",
        goal=(
            f"Combinar as informações de voos, hotéis e atividades para montar "
            f"3 roteiros completos e coerentes para {num_dias} dias em {destino}."
        ),
        backstory=(
            "Sou um arquiteto de viagens sênior com 20 anos de experiência montando "
            "pacotes personalizados para todos os perfis de viajante. "
            "Transformo dados brutos de voos, hotéis e atrações em experiências memoráveis, "
            "sempre equilibrando custo, conforto e enriquecimento cultural."
        ),
        tools=[ferramenta_dados],
        llm=llm,
        verbose=True,
    )

    tarefa = Task(
        description=(
            f"Use a ferramenta 'Consultar Dados dos Agentes' para obter os dados de voos, hotéis e atividades. "
            f"Monte 3 roteiros para {num_dias} dias em {destino}: econômico, conforto e premium. "
            "Para cada roteiro use o tier correspondente de voo e hotel. As atividades são as mesmas para todos. "
            "Calcule o custo total (voo + hotel × dias + atividades) e escreva um resumo de 2 frases. "
            "Retorne APENAS JSON válido no formato:\n"
            '{"economico": {"resumo": "", "custo_total": 0.0}, '
            '"conforto": {"resumo": "", "custo_total": 0.0}, '
            '"premium": {"resumo": "", "custo_total": 0.0}}'
        ),
        expected_output=(
            "JSON com 3 chaves (economico, conforto, premium), "
            "cada uma com 'resumo' (string) e 'custo_total' (número)."
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
        resumos_llm = json.loads(texto[inicio:fim])
    except (json.JSONDecodeError, ValueError):
        # Fallback completo — monta os roteiros sem o LLM
        return _montar_roteiros_fallback(voos, hoteis, atividades, num_dias), usage

    # Combina os resumos/custos do LLM com os dados brutos dos outros agentes
    roteiros = {}
    for nivel in ("economico", "conforto", "premium"):
        voo = voos.get(nivel, {})
        hotel = hoteis.get(nivel, {})
        dados_nivel = resumos_llm.get(nivel, {})

        ativs = atividades.get(nivel, [])
        roteiros[nivel] = {
            "resumo": dados_nivel.get("resumo", ""),
            "custo_total": dados_nivel.get("custo_total") or _calcular_custo(voo, hotel, ativs, num_dias),
            "voos": [voo] if voo else [],
            "hospedagens": [hotel] if hotel else [],
            "atividades": ativs,
        }

    return roteiros, usage
