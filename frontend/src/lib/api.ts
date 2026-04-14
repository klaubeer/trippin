const URL_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface OpcoesFetch extends RequestInit {
  token?: string;
}

async function requisitar<T>(caminho: string, opcoes: OpcoesFetch = {}): Promise<T> {
  const { token, ...fetchOpcoes } = opcoes;

  const cabecalhos: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOpcoes.headers as Record<string, string>),
  };

  if (token) {
    cabecalhos["Authorization"] = `Bearer ${token}`;
  }

  const resposta = await fetch(`${URL_BASE}${caminho}`, {
    ...fetchOpcoes,
    headers: cabecalhos,
  });

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(erro.detail ?? `Erro ${resposta.status}`);
  }

  return resposta.json();
}

// --- Auth ---
export const api = {
  auth: {
    async registrar(dados: { email: string; password: string; nome: string }) {
      return requisitar<{ id: string; email: string }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(dados),
      });
    },
    async entrar(email: string, senha: string): Promise<{ access_token: string }> {
      const form = new FormData();
      form.append("username", email);
      form.append("password", senha);
      const resposta = await fetch(`${URL_BASE}/api/auth/login`, {
        method: "POST",
        body: form,
      });
      if (!resposta.ok) throw new Error("Credenciais inválidas");
      return resposta.json();
    },
    async eu(token: string) {
      return requisitar<{ id: string; email: string; nome: string }>("/api/usuarios/me", { token });
    },
  },

  viagens: {
    async criar(
      dados: { origem: string; iata_origem: string; destino: string; iata_destino: string; data_inicio: string; data_fim: string; num_viajantes: number },
      token: string
    ) {
      return requisitar<{ id: string; status: string; slug: string }>("/api/viagens/", {
        method: "POST",
        body: JSON.stringify(dados),
        token,
      });
    },
    async listar(token: string) {
      return requisitar<SolicitacaoResumo[]>("/api/viagens/", { token });
    },
    async obter(id: string, token: string) {
      return requisitar<SolicitacaoCompleta>(`/api/viagens/${id}`, { token });
    },
  },

  monitoramento: {
    async historico(): Promise<ItemHistorico[]> {
      return requisitar<ItemHistorico[]>("/api/monitoramento/historico");
    },
  },

  compartilhar: {
    async obter(slug: string) {
      return requisitar<SolicitacaoCompleta>(`/api/compartilhar/${slug}`);
    },
  },

  pdf: {
    async baixar(id: string, nivel: string, token: string): Promise<Blob> {
      const resposta = await fetch(`${URL_BASE}/api/viagens/${id}/roteiros/${nivel}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resposta.ok) throw new Error("Erro ao gerar PDF");
      return resposta.blob();
    },
  },
};

// --- Tipos ---
export interface SolicitacaoResumo {
  id: string;
  origem: string;
  iata_origem: string;
  destino: string;
  iata_destino: string;
  data_inicio: string;
  data_fim: string;
  num_viajantes: number;
  status: "pendente" | "processando" | "concluido" | "falhou";
  slug: string;
  criado_em: string;
}

export interface Voo {
  id: string;
  companhia: string;
  partida: string;
  chegada: string;
  preco: number;
  link_reserva: string | null;
}

export interface Hospedagem {
  id: string;
  nome: string;
  tipo: string | null;
  preco_por_noite: number;
  avaliacao: number | null;
  link_reserva: string | null;
}

export interface Atividade {
  id: string;
  nome: string;
  dia: number;
  horario: string | null;
  descricao: string | null;
  custo_estimado: number | null;
  latitude: number | null;
  longitude: number | null;
}

export interface Roteiro {
  id: string;
  nivel: "economico" | "conforto" | "premium";
  custo_total_estimado: number | null;
  resumo: string | null;
  voos: Voo[];
  hospedagens: Hospedagem[];
  atividades: Atividade[];
}

export interface SolicitacaoCompleta extends SolicitacaoResumo {
  roteiros: Roteiro[];
}

export interface DetalheAgente {
  agente: "voos" | "hoteis" | "atividades" | "arquiteto";
  modelo: string;
  status: "concluido" | "falhou" | "iniciado";
  tokens_entrada: number | null;
  tokens_saida: number | null;
  tokens_total: number;
  custo_usd: number;
  duracao_segundos: number | null;
  fonte_dados: string | null;
}

export interface MetricasExecucao {
  total_tokens_entrada: number;
  total_tokens_saida: number;
  total_tokens: number;
  custo_usd: number;
  duracao_total_segundos: number;
}

export interface ItemHistorico {
  id: string;
  slug: string;
  origem: string;
  destino: string;
  data_inicio: string;
  data_fim: string;
  num_viajantes: number;
  status: "pendente" | "processando" | "concluido" | "falhou";
  criado_em: string;
  metricas: MetricasExecucao;
  agentes: DetalheAgente[];
}
