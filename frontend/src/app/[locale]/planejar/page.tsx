"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { useRouter } from "@/navegacao";
import { api } from "@/lib/api";
import { useSSE, ProgressoAgentes } from "@/lib/useSSE";
import AutocompleteLocal from "@/components/AutocompleteLocal";

type Etapa = "formulario" | "progresso" | "concluido";

const TOKEN_DEMO = ""; // preenchido via login demo

function FormularioViagem({
  onSubmit,
}: {
  onSubmit: (dados: {
    origem: string;
    iata_origem: string;
    destino: string;
    iata_destino: string;
    data_inicio: string;
    data_fim: string;
    num_viajantes: number;
  }) => void;
}) {
  const t = useTranslations("planejar");
  const [origem, setOrigem] = useState("");
  const [iataOrigem, setIataOrigem] = useState("");
  const [destino, setDestino] = useState("");
  const [iataDestino, setIataDestino] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [viajantes, setViajantes] = useState(1);
  const [erros, setErros] = useState<Record<string, string>>({});

  const validar = () => {
    const novosErros: Record<string, string> = {};
    const hoje = new Date().toISOString().split("T")[0];

    if (!origem) novosErros.origem = "Informe a cidade de origem";
    if (!destino) novosErros.destino = t("erroDestinoObrigatorio");
    if (!dataInicio || dataInicio <= hoje) novosErros.dataInicio = t("erroDatasPassadas");
    if (!dataFim || dataFim <= dataInicio) novosErros.dataFim = t("erroDatasOrdem");
    if (dataInicio && dataFim) {
      const dias = Math.floor(
        (new Date(dataFim).getTime() - new Date(dataInicio).getTime()) / 86400000
      );
      if (dias > 30) novosErros.dataFim = t("erroDuracaoMaxima");
    }

    setErros(novosErros);
    return Object.keys(novosErros).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validar()) return;
    onSubmit({
      origem,
      iata_origem: iataOrigem.toUpperCase() || "GRU",
      destino,
      iata_destino: iataDestino.toUpperCase() || "CDG",
      data_inicio: dataInicio,
      data_fim: dataFim,
      num_viajantes: viajantes,
    });
  };

  const campoDataStyle = "w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-white/40 transition [color-scheme:dark]";
  const labelStyle = "block text-sm font-medium text-white/70 mb-1";

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* Origem */}
      <div>
        <AutocompleteLocal
          label="✈️ Origem"
          placeholder="Ex: São Paulo, Rio de Janeiro..."
          onSelect={(local) => { setOrigem(local.nome); setIataOrigem(local.iata); }}
        />
        {erros.origem && <p className="text-red-400 text-sm mt-1">{erros.origem}</p>}
      </div>

      {/* Destino */}
      <div>
        <AutocompleteLocal
          label={`🏁 ${t("campoDestino")}`}
          placeholder={t("placeholderDestino")}
          onSelect={(local) => { setDestino(local.nome); setIataDestino(local.iata); }}
        />
        {erros.destino && <p className="text-red-400 text-sm mt-1">{erros.destino}</p>}
      </div>

      {/* Datas */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelStyle}>{t("campoDataInicio")}</label>
          <input
            type="date"
            value={dataInicio}
            onChange={(e) => setDataInicio(e.target.value)}
            min={new Date().toISOString().split("T")[0]}
            className={campoDataStyle}
          />
          {erros.dataInicio && <p className="text-red-400 text-sm mt-1">{erros.dataInicio}</p>}
        </div>
        <div>
          <label className={labelStyle}>{t("campoDataFim")}</label>
          <input
            type="date"
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
            min={dataInicio || new Date().toISOString().split("T")[0]}
            className={campoDataStyle}
          />
          {erros.dataFim && <p className="text-red-400 text-sm mt-1">{erros.dataFim}</p>}
        </div>
      </div>

      {/* Viajantes */}
      <div>
        <label className={labelStyle}>{t("campoViajantes")}</label>
        <select
          value={viajantes}
          onChange={(e) => setViajantes(Number(e.target.value))}
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-white/50 transition [color-scheme:dark]"
        >
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <option key={n} value={n} className="bg-zinc-900 text-white">
              {n} {n === 1 ? "viajante" : "viajantes"}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        className="w-full py-4 rounded-xl bg-white text-zinc-900 font-semibold text-lg hover:bg-white/90 transition shadow-lg"
      >
        {t("botaoGerar")}
      </button>
    </form>
  );
}

const NOMES_AGENTES = {
  voos: "✈️ Pesquisando voos",
  hoteis: "🏨 Buscando hotéis",
  atividades: "🗺️ Descobrindo atividades",
  arquiteto: "🧠 Montando roteiros",
};

function TelaProgresso({
  progresso,
  erro,
}: {
  progresso: ProgressoAgentes;
  erro: string | null;
}) {
  const t = useTranslations("progresso");

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-white mb-6">{t("titulo")}</h2>
      {(Object.keys(progresso) as Array<keyof ProgressoAgentes>).map((agente) => {
        const status = progresso[agente];
        return (
          <motion.div
            key={agente}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex items-center gap-4 p-4 rounded-xl border transition-colors ${
              status === "concluido"
                ? "bg-green-500/15 border-green-500/30"
                : status === "iniciando"
                ? "bg-white/15 border-white/30"
                : "bg-white/5 border-white/10"
            }`}
          >
            <div className="text-2xl">{NOMES_AGENTES[agente].split(" ")[0]}</div>
            <div className="flex-1">
              <p className="font-medium text-white/90">
                {NOMES_AGENTES[agente].slice(3)}
              </p>
            </div>
            <div>
              {status === "concluido" ? (
                <span className="text-green-400 font-medium">✓ Pronto</span>
              ) : status === "iniciando" ? (
                <motion.span
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1.2 }}
                  className="text-white/70 font-medium"
                >
                  Processando...
                </motion.span>
              ) : (
                <span className="text-white/30">Aguardando</span>
              )}
            </div>
          </motion.div>
        );
      })}
      {erro && (
        <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-300">
          {erro}
        </div>
      )}
    </div>
  );
}

export default function PaginaPlanejar() {
  const t = useTranslations("planejar");
  const router = useRouter();
  const [etapa, setEtapa] = useState<Etapa>("formulario");
  const [solicitacaoId, setSolicitacaoId] = useState<string | null>(null);
  const [token] = useState<string | null>(
    typeof window !== "undefined" ? localStorage.getItem("token") : null
  );
  const [erroGeral, setErroGeral] = useState<string | null>(null);

  const { progresso, finalizado, erro } = useSSE(
    etapa === "progresso" ? solicitacaoId : null,
    token
  );

  // Redireciona quando finalizado
  useEffect(() => {
    if (finalizado && solicitacaoId && etapa === "progresso") {
      router.push(`/roteiros/${solicitacaoId}`);
    }
  }, [finalizado, solicitacaoId, etapa, router]);

  const handleSubmit = async (dados: {
    origem: string;
    iata_origem: string;
    destino: string;
    iata_destino: string;
    data_inicio: string;
    data_fim: string;
    num_viajantes: number;
  }) => {
    try {
      const solicitacao = await api.viagens.criar(dados, token);
      setSolicitacaoId(solicitacao.id);
      setEtapa("progresso");
    } catch (err: unknown) {
      setErroGeral(err instanceof Error ? err.message : "Erro ao criar solicitação");
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-950 via-zinc-900 to-zinc-950 flex items-center justify-center p-8">
      <div className="w-full max-w-lg bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-2xl p-8">
        <h1 className="text-2xl font-bold text-white mb-8">
          {etapa === "formulario" ? t("titulo") : ""}
        </h1>

        <AnimatePresence mode="wait">
          {etapa === "formulario" && (
            <motion.div
              key="formulario"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {erroGeral && (
                <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
                  {erroGeral}
                </div>
              )}
              <FormularioViagem onSubmit={handleSubmit} />
            </motion.div>
          )}

          {etapa === "progresso" && (
            <motion.div
              key="progresso"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <TelaProgresso progresso={progresso} erro={erro} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
