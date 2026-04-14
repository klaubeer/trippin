"use client";

import { useEffect, useRef, useState } from "react";

const VIDEOS = [
  "/videos/praia_1.mp4",
  "/videos/montanha.mp4",
  "/videos/cidade.mp4",
  "/videos/mar.mp4",
];

const DURACAO_MS = 8000;

export default function VideoFundo() {
  const [ativo, setAtivo] = useState(0);
  const [proximo, setProximo] = useState<number | null>(null);
  const [transicionando, setTransicionando] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const avancar = () => {
    const prox = (ativo + 1) % VIDEOS.length;
    setProximo(prox);
    setTransicionando(true);

    setTimeout(() => {
      setAtivo(prox);
      setProximo(null);
      setTransicionando(false);
    }, 1000); // duração do crossfade
  };

  useEffect(() => {
    timerRef.current = setTimeout(avancar, DURACAO_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [ativo]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Vídeo atual */}
      <video
        key={`ativo-${ativo}`}
        src={VIDEOS[ativo]}
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 w-full h-full object-cover"
        style={{
          opacity: transicionando ? 0 : 1,
          transition: "opacity 1s ease-in-out",
        }}
      />

      {/* Vídeo seguinte (aparece durante crossfade) */}
      {proximo !== null && (
        <video
          key={`proximo-${proximo}`}
          src={VIDEOS[proximo]}
          autoPlay
          muted
          loop
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
          style={{
            opacity: transicionando ? 1 : 0,
            transition: "opacity 1s ease-in-out",
          }}
        />
      )}

      {/* Overlay escuro degradê para legibilidade */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />

      {/* Indicadores de progresso (bolinha) */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 z-10">
        {VIDEOS.map((_, i) => (
          <button
            key={i}
            onClick={() => {
              if (timerRef.current) clearTimeout(timerRef.current);
              setAtivo(i);
            }}
            className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
              i === ativo ? "bg-white w-4" : "bg-white/40"
            }`}
            aria-label={`Vídeo ${i + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
