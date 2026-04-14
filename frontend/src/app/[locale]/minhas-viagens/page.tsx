"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/navegacao";
import { api, SolicitacaoResumo } from "@/lib/api";

const COR_STATUS = {
  pendente: "bg-zinc-100 text-zinc-600",
  processando: "bg-blue-100 text-blue-700",
  concluido: "bg-green-100 text-green-700",
  falhou: "bg-red-100 text-red-700",
};

export default function PaginaMinhasViagens() {
  const t = useTranslations("minhasViagens");
  const [viagens, setViagens] = useState<SolicitacaoResumo[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    const carregar = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;
      const dados = await api.viagens.listar(token);
      setViagens(dados);
      setCarregando(false);
    };
    carregar();
  }, []);

  if (carregando) {
    return (
      <main className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="text-zinc-500">Carregando...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-zinc-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-zinc-900 mb-6">{t("titulo")}</h1>

        {viagens.length === 0 ? (
          <div className="text-center py-16 text-zinc-500">
            <p className="text-lg mb-4">{t("semViagens")}</p>
            <Link
              href="/planejar"
              className="px-6 py-3 rounded-xl bg-blue-900 text-white hover:bg-blue-800 transition font-medium"
            >
              Planejar agora
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {viagens.map((viagem) => (
              <Link
                key={viagem.id}
                href={`/roteiros/${viagem.id}`}
                className="block p-5 bg-white rounded-xl border border-zinc-200 hover:border-blue-300 hover:shadow-sm transition"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-zinc-900 text-lg">{viagem.destino}</h2>
                    <p className="text-sm text-zinc-500 mt-1">
                      {new Date(viagem.data_inicio).toLocaleDateString("pt-BR")} →{" "}
                      {new Date(viagem.data_fim).toLocaleDateString("pt-BR")} ·{" "}
                      {viagem.num_viajantes} viajante(s)
                    </p>
                    <p className="text-xs text-zinc-400 mt-1">
                      {new Date(viagem.criado_em).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "long",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-3 py-1 rounded-full ${
                      COR_STATUS[viagem.status]
                    }`}
                  >
                    {t(`status${viagem.status.charAt(0).toUpperCase() + viagem.status.slice(1)}` as any)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
