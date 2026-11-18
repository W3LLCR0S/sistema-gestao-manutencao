import type { ReactNode } from "react";
import { Inbox, Loader2, TriangleAlert } from "lucide-react";

export function Carregando({ texto = "Carregando…", tela = false }: { texto?: string; tela?: boolean }) {
  return (
    <div className={tela ? "estado estado--tela" : "estado"} role="status" aria-live="polite">
      <Loader2 className="girar" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}

export function Vazio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="vazio">
      <Inbox aria-hidden="true" size={32} />
      <h3>{titulo}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErroCarga({ mensagem, aoTentar }: { mensagem: string; aoTentar?: () => void }) {
  return (
    <div className="alerta alerta--erro" role="alert">
      <TriangleAlert aria-hidden="true" size={20} />
      <div>
        <strong>Não foi possível carregar.</strong>
        <p>{mensagem}</p>
        {aoTentar && (
          <button type="button" className="btn btn--sec" onClick={aoTentar}>
            Tentar novamente
          </button>
        )}
      </div>
    </div>
  );
}

export function Alerta({ tipo = "erro", children }: { tipo?: "erro" | "info" | "ok"; children: ReactNode }) {
  return (
    <div className={`alerta alerta--${tipo}`} role={tipo === "erro" ? "alert" : "status"}>
      <div>{children}</div>
    </div>
  );
}
