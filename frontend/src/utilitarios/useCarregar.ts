import { useCallback, useEffect, useRef, useState } from "react";
import { mensagemDeErro } from "../api/cliente";

export interface Carregamento<T> {
  dados: T | null;
  carregando: boolean;
  erro: string | null;
  recarregar: () => void;
}

/** Carrega dados da API e permite recarregar (usado após mutações). Ignora respostas obsoletas. */
export function useCarregar<T>(buscar: () => Promise<T>, dependencias: unknown[] = []): Carregamento<T> {
  const [dados, setDados] = useState<T | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const ultima = useRef(0);
  const buscarRef = useRef(buscar);
  buscarRef.current = buscar;

  useEffect(() => {
    const id = ++ultima.current;
    setCarregando(true);
    buscarRef
      .current()
      .then((d) => {
        if (id !== ultima.current) return;
        setDados(d);
        setErro(null);
      })
      .catch((e) => {
        if (id !== ultima.current) return;
        setErro(mensagemDeErro(e));
      })
      .finally(() => {
        if (id === ultima.current) setCarregando(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versao, ...dependencias]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  return { dados, carregando, erro, recarregar };
}
