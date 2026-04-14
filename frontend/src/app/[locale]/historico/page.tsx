"use client";

import { useEffect, useState } from "react";
import { Link } from "@/navegacao";
import { api, ItemHistorico, DetalheAgente } from "@/lib/api";

const COR_STATUS: Record<string, string> = {
  pendente: "bg-zinc-700 text-zinc-300",
  processando: "bg-blue-900/60 text-blue-300",
  concluido: "bg-emerald-900/60 text-emerald-300",
  falhou: "bg-red-900/60 text-red-300",
};

const NOME_AGENTE: Record<string, string> = {
  voos: "Voos",
  hoteis: "Hotéis",
  atividades: "Atividades",
  arquiteto: "Arquiteto",
};

const COR_AGENTE: Record<string, string> = {
  voos: "text-blue-400",
  hoteis: "text-violet-400",
  atividades: "text-emerald-400",
  arquiteto: "text-amber-400",
};

function fmt(n: number, casas = 0): string {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function fmtUsd(n: number): string {
  return `$${n.toFixed(4)}`;
}

function fmtSeg(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const seg = (s % 60).toFixed(0);
  return `${m}m ${seg}s`;
}

function CardAgente({ ag }: { ag: DetalheAgente }) {
  return (
    <div className="flex items-center gap-3 py-2 border-t border-white/5">
      <div className={`text-xs font-mono font-semibold w-20 shrink-0 ${COR_AGENTE[ag.agente]}`}>
        {NOME_AGENTE[ag.agente]}
      </div>
      <div className="text-xs text-white/50 font-mono w-36 shrink-0 truncate" title={ag.modelo}>
        {ag.modelo.replace("openai/", "")}
      </div>
      <div className="flex gap-4 flex-1 text-xs text-white/70 font-mono">
        <span title="Tokens de entrada">{fmt(ag.tokens_entrada ?? 0)}↑</span>
        <span title="Tokens de saída">{fmt(ag.tokens_saida ?? 0)}↓</span>
        <span className="font-semibold" title="Total tokens">{fmt(ag.tokens_total)} tok</span>
        <span className="text-amber-400" title="Custo USD">{fmtUsd(ag.custo_usd)}</span>
        <span className="text-white/40" title="Duração">{fmtSeg(ag.duracao_segundos ?? 0)}</span>
      </div>
      <div className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${ag.status === "concluido" ? "bg-emerald-900/40 text-emerald-400" : "bg-red-900/40 text-red-400"}`}>
        {ag.status}
      </div>
    </div>
  );
}

function CardViagem({ item, expandido, onToggle }: { item: ItemHistorico; expandido: boolean; onToggle: () => void }) {
  const dias = Math.ceil(
    (new Date(item.data_fim).getTime() - new Date(item.data_inicio).getTime()) / 86400000
  );

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
      {/* Cabeçalho */}
      <button
        onClick={onToggle}
        className="w-full text-left p-4 hover:bg-white/5 transition"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-white">{item.destino}</span>
              <span className="text-white/40 text-sm">← {item.origem}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${COR_STATUS[item.status]}`}>
                {item.status}
              </span>
            </div>
            <div className="text-xs text-white/50">
              {new Date(item.data_inicio).toLocaleDateString("pt-BR")} →{" "}
              {new Date(item.data_fim).toLocaleDateString("pt-BR")} · {dias} dias · {item.num_viajantes} pax
            </div>
            <div className="text-xs text-white/30 mt-0.5">
              {new Date(item.criado_em).toLocaleString("pt-BR")}
            </div>
          </div>

          {/* Métricas resumidas */}
          {item.metricas.total_tokens > 0 && (
            <div className="shrink-0 text-right">
              <div className="text-sm font-mono font-semibold text-amber-400">
                {fmtUsd(item.metricas.custo_usd)}
              </div>
              <div className="text-xs text-white/50 font-mono">
                {fmt(item.metricas.total_tokens)} tokens
              </div>
              <div className="text-xs text-white/40 font-mono">
                {fmtSeg(item.metricas.duracao_total_segundos)}
              </div>
            </div>
          )}

          {/* Chevron */}
          <div className={`text-white/30 transition-transform ${expandido ? "rotate-180" : ""}`}>
            ▾
          </div>
        </div>
      </button>

      {/* Detalhes expandíveis */}
      {expandido && (
        <div className="px-4 pb-4 border-t border-white/10">
          {/* Sumário total */}
          {item.metricas.total_tokens > 0 && (
            <div className="grid grid-cols-4 gap-3 py-3 mb-2">
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-mono font-bold text-white">{fmt(item.metricas.total_tokens)}</div>
                <div className="text-xs text-white/50">tokens totais</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-mono font-bold text-amber-400">{fmtUsd(item.metricas.custo_usd)}</div>
                <div className="text-xs text-white/50">custo USD</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-mono font-bold text-blue-400">{fmtSeg(item.metricas.duracao_total_segundos)}</div>
                <div className="text-xs text-white/50">duração total</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-mono font-bold text-white/70">{fmt(item.metricas.total_tokens_entrada)}↑ / {fmt(item.metricas.total_tokens_saida)}↓</div>
                <div className="text-xs text-white/50">input / output</div>
              </div>
            </div>
          )}

          {/* Breakdown por agente */}
          {item.agentes.length > 0 ? (
            <div>
              <div className="text-xs text-white/30 uppercase tracking-wider mb-1">Breakdown por agente</div>
              {item.agentes.map((ag) => (
                <CardAgente key={ag.agente} ag={ag} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-white/30 py-2">Sem logs de execução registrados.</p>
          )}

          {/* Link para o roteiro */}
          {item.status === "concluido" && (
            <Link
              href={`/roteiros/${item.id}`}
              className="mt-3 inline-block text-xs text-blue-400 hover:text-blue-300 transition"
            >
              Ver roteiros completos →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function PaginaHistorico() {
  const [historico, setHistorico] = useState<ItemHistorico[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [expandido, setExpandido] = useState<string | null>(null);

  useEffect(() => {
    api.monitoramento.historico()
      .then(setHistorico)
      .finally(() => setCarregando(false));
  }, []);

  // Totais agregados
  const totalTokens = historico.reduce((s, i) => s + i.metricas.total_tokens, 0);
  const totalCusto = historico.reduce((s, i) => s + i.metricas.custo_usd, 0);
  const totalConcluidos = historico.filter(i => i.status === "concluido").length;

  return (
    <main className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-blue-950 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">Histórico de Execuções</h1>
          <p className="text-sm text-white/50">Monitoramento de uso, tokens e custos por roteiro gerado</p>
        </div>

        {/* Resumo geral */}
        {!carregando && historico.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-white">{historico.length}</div>
              <div className="text-xs text-white/50 mt-1">solicitações totais</div>
              <div className="text-xs text-emerald-400 mt-0.5">{totalConcluidos} concluídas</div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold font-mono text-white">{fmt(totalTokens)}</div>
              <div className="text-xs text-white/50 mt-1">tokens consumidos</div>
              <div className="text-xs text-white/30 mt-0.5">
                ~{fmt(totalConcluidos > 0 ? totalTokens / totalConcluidos : 0)} por roteiro
              </div>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold font-mono text-amber-400">{fmtUsd(totalCusto)}</div>
              <div className="text-xs text-white/50 mt-1">custo total USD</div>
              <div className="text-xs text-white/30 mt-0.5">
                ~{fmtUsd(totalConcluidos > 0 ? totalCusto / totalConcluidos : 0)} por roteiro
              </div>
            </div>
          </div>
        )}

        {/* Lista */}
        {carregando ? (
          <div className="text-center py-16 text-white/50">Carregando histórico...</div>
        ) : historico.length === 0 ? (
          <div className="text-center py-16 text-white/40">
            <p className="text-lg">Nenhuma solicitação registrada ainda.</p>
            <Link href="/planejar" className="mt-4 inline-block text-blue-400 hover:text-blue-300 transition">
              Gerar primeiro roteiro →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {historico.map((item) => (
              <CardViagem
                key={item.id}
                item={item}
                expandido={expandido === item.id}
                onToggle={() => setExpandido(expandido === item.id ? null : item.id)}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
