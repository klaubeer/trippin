"use client";

import { useEffect, useRef, useState } from "react";

interface Local {
  nome: string;
  iata: string;
  pais: string;
}

interface Props {
  placeholder: string;
  label: string;
  onSelect: (local: Local) => void;
}

const URL_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AutocompleteLocal({ placeholder, label, onSelect }: Props) {
  const [valor, setValor] = useState("");
  const [sugestoes, setSugestoes] = useState<Local[]>([]);
  const [aberto, setAberto] = useState(false);
  const [selecionado, setSelecionado] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fecha o dropdown ao clicar fora
  useEffect(() => {
    function handleClickFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  // Busca com debounce de 300ms
  useEffect(() => {
    if (selecionado) return;
    if (valor.length < 2) {
      setSugestoes([]);
      setAberto(false);
      return;
    }

    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${URL_BASE}/api/locais?q=${encodeURIComponent(valor)}`);
        if (res.ok) {
          const dados: Local[] = await res.json();
          setSugestoes(dados);
          setAberto(dados.length > 0);
        }
      } catch {
        // silencia erros de rede — o campo ainda funciona como texto livre
      }
    }, 300);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [valor, selecionado]);

  function handleSelecionar(local: Local) {
    setValor(local.nome);
    setSugestoes([]);
    setAberto(false);
    setSelecionado(true);
    onSelect(local);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setValor(e.target.value);
    setSelecionado(false); // permite nova busca se o usuário editar
  }

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-sm font-medium text-white/70 mb-1">{label}</label>
      <input
        type="text"
        value={valor}
        onChange={handleChange}
        placeholder={placeholder}
        autoComplete="off"
        className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-white/40 transition"
      />
      {aberto && sugestoes.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-zinc-900 border border-white/20 rounded-xl shadow-2xl overflow-hidden">
          {sugestoes.map((local) => (
            <li
              key={local.iata}
              onMouseDown={() => handleSelecionar(local)}
              className="flex items-center justify-between px-4 py-3 hover:bg-white/10 cursor-pointer transition"
            >
              <div>
                <span className="text-white font-medium">{local.nome}</span>
                <span className="text-white/50 text-sm ml-2">{local.pais}</span>
              </div>
              <span className="text-white/40 text-xs font-mono">{local.iata}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
