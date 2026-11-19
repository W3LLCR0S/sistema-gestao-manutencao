import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { CircleCheck, CircleX, X } from "lucide-react";

interface Aviso {
  id: number;
  tipo: "ok" | "erro";
  texto: string;
}
interface Ctx {
  ok: (t: string) => void;
  erro: (t: string) => void;
}
const Contexto = createContext<Ctx | null>(null);

export function ProvedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const proximo = useRef(1);
  const remover = useCallback((id: number) => setAvisos((a) => a.filter((x) => x.id !== id)), []);
  const adicionar = useCallback(
    (tipo: Aviso["tipo"], texto: string) => {
      const id = proximo.current++;
      setAvisos((a) => [...a.slice(-3), { id, tipo, texto }]);
      window.setTimeout(() => remover(id), tipo === "erro" ? 8000 : 4500);
    },
    [remover],
  );
  const valor = useMemo<Ctx>(
    () => ({ ok: (t) => adicionar("ok", t), erro: (t) => adicionar("erro", t) }),
    [adicionar],
  );
  return (
    <Contexto.Provider value={valor}>
      {children}
      <div className="avisos" aria-live="polite" aria-atomic="false">
        {avisos.map((a) => (
          <div key={a.id} className={`aviso aviso--${a.tipo}`} role={a.tipo === "erro" ? "alert" : "status"}>
            {a.tipo === "ok" ? <CircleCheck aria-hidden="true" /> : <CircleX aria-hidden="true" />}
            <span>{a.texto}</span>
            <button type="button" className="btn-icone" onClick={() => remover(a.id)} aria-label="Dispensar aviso">
              <X aria-hidden="true" size={16} />
            </button>
          </div>
        ))}
      </div>
    </Contexto.Provider>
  );
}

export function useAvisos(): Ctx {
  const c = useContext(Contexto);
  if (!c) throw new Error("useAvisos fora do ProvedorAvisos");
  return c;
}
