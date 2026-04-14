"use client";

import { useEffect, useRef, useState } from "react";

export type StatusAgente = "aguardando" | "iniciando" | "concluido" | "erro";

export interface EventoProgresso {
  agente?: "voos" | "hoteis" | "atividades" | "arquiteto";
  status?: "iniciando" | "concluido";
  tipo?: "finalizado" | "erro";
  mensagem?: string;
}

export interface ProgressoAgentes {
  voos: StatusAgente;
  hoteis: StatusAgente;
  atividades: StatusAgente;
  arquiteto: StatusAgente;
}

const ESTADO_INICIAL: ProgressoAgentes = {
  voos: "aguardando",
  hoteis: "aguardando",
  atividades: "aguardando",
  arquiteto: "aguardando",
};

export function useSSE(solicitacaoId: string | null, token: string | null) {
  const [progresso, setProgresso] = useState<ProgressoAgentes>(ESTADO_INICIAL);
  const [finalizado, setFinalizado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const fonteRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!solicitacaoId) return;

    const urlBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const url = token
      ? `${urlBase}/api/viagens/${solicitacaoId}/stream?token=${token}`
      : `${urlBase}/api/viagens/${solicitacaoId}/stream`;
    const fonte = new EventSource(url);

    fonteRef.current = fonte;

    fonte.onmessage = (evento) => {
      const dados: EventoProgresso = JSON.parse(evento.data);

      if (dados.agente && dados.status) {
        setProgresso((anterior) => ({
          ...anterior,
          [dados.agente!]: dados.status as StatusAgente,
        }));
      }

      if (dados.tipo === "finalizado") {
        setFinalizado(true);
        fonte.close();
      }

      if (dados.tipo === "erro") {
        setErro(dados.mensagem ?? "Erro desconhecido");
        fonte.close();
      }
    };

    fonte.onerror = () => {
      setErro("Conexão perdida com o servidor");
      fonte.close();
    };

    return () => {
      fonte.close();
    };
  }, [solicitacaoId, token]);

  return { progresso, finalizado, erro };
}
