import { api, SolicitacaoCompleta } from "@/lib/api";
import { notFound } from "next/navigation";

export default async function PaginaCompartilhar({
  params,
}: PageProps<"/[locale]/compartilhar/[slug]">) {
  const { slug } = await params;

  let solicitacao: SolicitacaoCompleta;
  try {
    solicitacao = await api.compartilhar.obter(slug);
  } catch {
    notFound();
  }

  return (
    <main className="min-h-screen bg-zinc-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm">
          📎 Roteiro compartilhado — visualização pública
        </div>
        <h1 className="text-2xl font-bold text-zinc-900 mb-2">
          {solicitacao.destino}
        </h1>
        <p className="text-zinc-500 text-sm mb-6">
          {new Date(solicitacao.data_inicio).toLocaleDateString("pt-BR")} →{" "}
          {new Date(solicitacao.data_fim).toLocaleDateString("pt-BR")} ·{" "}
          {solicitacao.num_viajantes} viajante(s)
        </p>

        {solicitacao.roteiros.length === 0 ? (
          <div className="text-zinc-500">Roteiros ainda não disponíveis.</div>
        ) : (
          <div className="space-y-6">
            {solicitacao.roteiros.map((roteiro) => (
              <div key={roteiro.id} className="bg-white rounded-xl border border-zinc-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-semibold capitalize text-zinc-800">{roteiro.nivel}</h2>
                  {roteiro.custo_total_estimado && (
                    <span className="font-bold text-zinc-900">
                      R$ {Number(roteiro.custo_total_estimado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                    </span>
                  )}
                </div>
                {roteiro.resumo && (
                  <p className="text-zinc-600 text-sm">{roteiro.resumo}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
