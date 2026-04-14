"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useRouter } from "@/navegacao";
import { Link } from "@/navegacao";
import dynamic from "next/dynamic";
import { api, SolicitacaoCompleta, Roteiro } from "@/lib/api";

// Leaflet precisa ser importado dinamicamente (sem SSR)
const MapaAtividades = dynamic(() => import("@/components/mapa/MapaAtividades"), {
  ssr: false,
  loading: () => <div className="h-64 bg-zinc-800 rounded-xl animate-pulse" />,
});

const LABELS_NIVEL = {
  economico: { label: "Econômico", cor: "from-blue-600 to-blue-700" },
  conforto: { label: "Conforto", cor: "from-indigo-600 to-indigo-700" },
  premium: { label: "Premium", cor: "from-violet-600 to-violet-700" },
} as const;

function CardVoo({ voo }: { voo: ReturnType<typeof Object.values>[number] }) {
  return (
    <div className="p-4 bg-zinc-800/60 border border-zinc-700/50 rounded-xl">
      <div className="flex justify-between items-start gap-4">
        <div>
          <p className="font-semibold text-white">{(voo as any).companhia}</p>
          <p className="text-sm text-zinc-400 mt-0.5">
            {new Date((voo as any).partida).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
            {" → "}
            {new Date((voo as any).chegada).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}
          </p>
        </div>
        <p className="font-bold text-white whitespace-nowrap">
          R$ {Number((voo as any).preco).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
        </p>
      </div>
    </div>
  );
}

function AtividadesDosDias({ atividades }: { atividades: Roteiro["atividades"] }) {
  const diasUnicos = [...new Set(atividades.map((a) => a.dia))].sort((a, b) => a - b);
  return (
    <div className="space-y-4">
      {diasUnicos.map((dia) => (
        <div key={dia}>
          <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-2">
            Dia {dia}
          </h4>
          <div className="space-y-2">
            {atividades
              .filter((a) => a.dia === dia)
              .map((ativ) => (
                <div key={ativ.id} className="p-3 bg-zinc-800/60 border border-zinc-700/50 rounded-xl">
                  <div className="flex justify-between items-start gap-2">
                    <p className="font-medium text-white text-sm">{ativ.nome}</p>
                    {ativ.custo_estimado != null && (
                      <p className="text-xs text-zinc-400 whitespace-nowrap">
                        {Number(ativ.custo_estimado) === 0
                          ? "Gratuito"
                          : `R$ ${Number(ativ.custo_estimado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                      </p>
                    )}
                  </div>
                  {ativ.descricao && (
                    <p className="text-xs text-zinc-500 mt-1">{ativ.descricao}</p>
                  )}
                  {ativ.horario && (
                    <p className="text-xs text-zinc-600 mt-1">🕐 {ativ.horario.slice(0, 5)}</p>
                  )}
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function PainelRoteiro({ roteiro, solicitacaoId }: { roteiro: Roteiro; solicitacaoId: string }) {
  const t = useTranslations("roteiro");
  const [abaAtiva, setAbaAtiva] = useState<"atividades" | "mapa">("atividades");
  const [linkCopiado, setLinkCopiado] = useState(false);
  const [baixandoPdf, setBaixandoPdf] = useState(false);

  const token = typeof window !== "undefined" ? (localStorage.getItem("token") ?? "") : "";
  const usuarioLogado = !!token;

  const coordenadas = roteiro.atividades
    .filter((a) => a.latitude && a.longitude)
    .map((a) => ({ lat: a.latitude!, lng: a.longitude!, nome: a.nome }));

  const handleBaixarPdf = async () => {
    if (!token) return;
    setBaixandoPdf(true);
    try {
      const blob = await api.pdf.baixar(roteiro.id, roteiro.nivel, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `trippin-roteiro-${roteiro.nivel}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setBaixandoPdf(false);
    }
  };

  const handleCompartilhar = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setLinkCopiado(true);
    setTimeout(() => setLinkCopiado(false), 2500);
  };

  return (
    <div className="space-y-5">
      {/* Resumo */}
      {roteiro.resumo && (
        <div className="p-4 bg-zinc-800/40 border border-zinc-700/40 rounded-xl">
          <p className="text-zinc-300 text-sm leading-relaxed">{roteiro.resumo}</p>
        </div>
      )}

      {/* Custo total */}
      {roteiro.custo_total_estimado && (
        <div className="flex items-center justify-between p-4 bg-zinc-800/40 border border-zinc-700/40 rounded-xl">
          <span className="text-zinc-400 text-sm">{t("custoTotal")}</span>
          <span className="text-xl font-bold text-white">
            R$ {Number(roteiro.custo_total_estimado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
          </span>
        </div>
      )}

      {/* Voos */}
      {roteiro.voos.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">✈️ {t("voos")}</h3>
          <div className="space-y-2">
            {roteiro.voos.map((voo) => <CardVoo key={voo.id} voo={voo} />)}
          </div>
        </div>
      )}

      {/* Hospedagem */}
      {roteiro.hospedagens.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-400 mb-2">🏨 {t("hospedagem")}</h3>
          <div className="space-y-2">
            {roteiro.hospedagens.map((h) => (
              <div key={h.id} className="p-4 bg-zinc-800/60 border border-zinc-700/50 rounded-xl">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <p className="font-semibold text-white text-sm">{h.nome}</p>
                    {h.tipo && <p className="text-xs text-zinc-500 mt-0.5">{h.tipo}</p>}
                    {h.avaliacao && <p className="text-xs text-amber-400 mt-0.5">★ {h.avaliacao}</p>}
                  </div>
                  <p className="font-bold text-white text-sm whitespace-nowrap">
                    R$ {Number(h.preco_por_noite).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}/noite
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Atividades / Mapa */}
      <div>
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setAbaAtiva("atividades")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
              abaAtiva === "atividades"
                ? "bg-white text-zinc-900"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            🗺️ {t("atividades")}
          </button>
          <button
            onClick={() => setAbaAtiva("mapa")}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
              abaAtiva === "mapa"
                ? "bg-white text-zinc-900"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            📍 {t("mapa")}
          </button>
        </div>

        {abaAtiva === "atividades" && (
          <AtividadesDosDias atividades={roteiro.atividades} />
        )}
        {abaAtiva === "mapa" && (
          <MapaAtividades pontos={coordenadas} />
        )}
      </div>

      {/* Ações */}
      <div className="flex gap-3 pt-4 border-t border-zinc-800">
        <button
          onClick={handleCompartilhar}
          className="flex-1 py-3 rounded-xl border border-zinc-700 text-zinc-300 hover:bg-zinc-800 transition text-sm font-medium"
        >
          {linkCopiado ? "✅ Link copiado!" : `🔗 ${t("compartilhar")}`}
        </button>

        {usuarioLogado ? (
          <button
            onClick={handleBaixarPdf}
            disabled={baixandoPdf}
            className="flex-1 py-3 rounded-xl bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white transition text-sm font-medium"
          >
            {baixandoPdf ? "Gerando..." : `📄 ${t("baixarPdf")}`}
          </button>
        ) : (
          <div className="flex-1 relative group">
            <button
              disabled
              className="w-full py-3 rounded-xl bg-zinc-800 text-zinc-500 text-sm font-medium cursor-not-allowed"
            >
              📄 {t("baixarPdf")}
            </button>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-zinc-700 text-zinc-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none">
              Faça login para baixar o PDF
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PaginaRoteiro() {
  const t = useTranslations("roteiro");
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [solicitacao, setSolicitacao] = useState<SolicitacaoCompleta | null>(null);
  const [nivelAtivo, setNivelAtivo] = useState<"economico" | "conforto" | "premium">("economico");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const carregar = async () => {
      const token = localStorage.getItem("token") ?? "";
      try {
        const dados = await api.viagens.obter(id, token);
        setSolicitacao(dados);
      } catch (e) {
        setErro(e instanceof Error ? e.message : "Erro desconhecido");
      } finally {
        setCarregando(false);
      }
    };
    carregar();
  }, [id]);

  const roteiroAtivo = solicitacao?.roteiros.find((r) => r.nivel === nivelAtivo);

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-950 via-zinc-900 to-zinc-950 text-white">
      {/* Nav */}
      <nav className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800/60">
        <Link href="/" className="text-xl font-bold tracking-tight text-white hover:text-zinc-300 transition">
          Trippin&apos;
        </Link>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white transition"
        >
          ← Voltar
        </button>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {carregando && (
          <div className="flex items-center justify-center py-24">
            <p className="text-zinc-500">Carregando roteiros...</p>
          </div>
        )}

        {erro && (
          <div className="flex flex-col items-center justify-center py-24 gap-2">
            <p className="text-red-400 font-medium">Erro ao carregar roteiro</p>
            <p className="text-zinc-500 text-sm">{erro}</p>
            <button
              onClick={() => router.push("/")}
              className="mt-4 px-5 py-2 rounded-full bg-zinc-800 text-zinc-300 hover:bg-zinc-700 text-sm transition"
            >
              Ir para o início
            </button>
          </div>
        )}

        {!carregando && !erro && solicitacao && (
          <>
            {/* Header da viagem */}
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-white">{solicitacao.destino}</h1>
              <p className="text-zinc-400 text-sm mt-1">
                {solicitacao.origem} ({solicitacao.iata_origem}) → {solicitacao.destino} ({solicitacao.iata_destino}) ·{" "}
                {new Date(solicitacao.data_inicio + "T12:00:00").toLocaleDateString("pt-BR")} →{" "}
                {new Date(solicitacao.data_fim + "T12:00:00").toLocaleDateString("pt-BR")} ·{" "}
                {solicitacao.num_viajantes} viajante(s)
              </p>
            </div>

            {/* Tabs de nível */}
            <div className="flex gap-2 mb-6">
              {(["economico", "conforto", "premium"] as const).map((nivel) => (
                <button
                  key={nivel}
                  onClick={() => setNivelAtivo(nivel)}
                  className={`px-5 py-2 rounded-full font-medium text-sm transition ${
                    nivelAtivo === nivel
                      ? "bg-white text-zinc-900 shadow"
                      : "bg-zinc-800/60 text-zinc-400 border border-zinc-700/50 hover:bg-zinc-700/60"
                  }`}
                >
                  {t(nivel)}
                </button>
              ))}
            </div>

            {roteiroAtivo && (
              <PainelRoteiro roteiro={roteiroAtivo} solicitacaoId={solicitacao.id} />
            )}
          </>
        )}
      </div>
    </main>
  );
}
