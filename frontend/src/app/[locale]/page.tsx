import { useTranslations } from "next-intl";
import { Link } from "@/navegacao";
import VideoFundoDinamico from "@/components/video/VideoFundoDinamico";

export default function PaginaInicial() {
  const t = useTranslations();

  return (
    <main className="min-h-screen text-white overflow-x-hidden">

      {/* ── Seção Hero com vídeo ── */}
      <section className="relative min-h-screen flex flex-col">
        <VideoFundoDinamico />

        {/* Conteúdo sobre o vídeo */}
        <div className="relative z-10 flex flex-col min-h-screen">

          {/* Nav */}
          <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto w-full">
            <span className="text-2xl font-bold tracking-tight drop-shadow-md">
              Trippin&apos;
            </span>
            <div className="flex gap-3">
              <Link
                href="/planejar"
                className="px-4 py-2 rounded-full border border-white/40 hover:bg-white/15 transition text-sm backdrop-blur-sm"
              >
                {t("navegacao.entrar")}
              </Link>
              <Link
                href="/planejar"
                className="px-4 py-2 rounded-full bg-white text-zinc-900 hover:bg-white/90 transition text-sm font-semibold shadow-lg"
              >
                {t("navegacao.criarConta")}
              </Link>
            </div>
          </nav>

          {/* Hero text — centralizado verticalmente */}
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6 pb-24">
            <h1 className="text-5xl md:text-7xl font-bold leading-[1.08] mb-6 drop-shadow-xl max-w-4xl">
              {t("inicio.titulo")}
            </h1>

            <p className="text-lg md:text-xl text-white/75 max-w-2xl mb-12 leading-relaxed drop-shadow">
              {t("inicio.subtitulo")}
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                href="/planejar"
                className="px-9 py-4 rounded-full bg-white text-zinc-900 hover:bg-white/90 transition font-semibold text-lg shadow-2xl"
              >
                {t("inicio.ctaPrincipal")}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Seção Features ── */}
      <section className="bg-zinc-950 py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-xs uppercase tracking-widest text-zinc-500 mb-3">
            Como funciona
          </p>
          <h2 className="text-center text-3xl md:text-4xl font-bold text-white mb-16">
            Tudo que você precisa,<br className="hidden md:block" /> num só lugar
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: "✈️",
                titulo: "Voos",
                desc: "Compare opções de voo da sua cidade em 3 faixas de preço — do econômico ao premium.",
              },
              {
                icon: "🏨",
                titulo: "Hospedagem",
                desc: "De hostels com custo-benefício a hotéis boutique e resorts de luxo.",
              },
              {
                icon: "🗺️",
                titulo: "Roteiro",
                desc: "Itinerário dia a dia com atrações, restaurantes e experiências locais no mapa.",
              },
            ].map((item) => (
              <div
                key={item.titulo}
                className="group bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-600 rounded-2xl p-7 transition-all duration-300"
              >
                <div className="text-4xl mb-4">{item.icon}</div>
                <h3 className="font-semibold text-lg text-white mb-2">{item.titulo}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA final ── */}
      <section className="bg-zinc-900 py-20 px-6 text-center border-t border-zinc-800">
        <p className="text-xs uppercase tracking-widest text-zinc-500 mb-3">Pronto para embarcar?</p>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
          Sua próxima aventura<br className="hidden md:block" /> começa agora
        </h2>
        <Link
          href="/planejar"
          className="inline-block px-10 py-4 rounded-full bg-white text-zinc-900 hover:bg-zinc-100 transition font-semibold text-lg shadow-xl"
        >
          Planejar minha viagem
        </Link>
      </section>

    </main>
  );
}
