import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

const FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface Props {
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
  largo?: boolean;
}

/** Diálogo modal acessível: foco preso, Esc fecha, foco volta ao elemento que abriu. */
export function Modal({ titulo, aoFechar, children, largo }: Props) {
  const idTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const fechar = useRef(aoFechar);
  fechar.current = aoFechar;

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    const caixaAtual = caixa.current;
    const primeiro = caixaAtual?.querySelector<HTMLElement>("input, select, textarea") ?? caixaAtual;
    primeiro?.focus();
    const corpo = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        fechar.current();
        return;
      }
      if (e.key !== "Tab" || !caixaAtual) return;
      const itens = Array.from(caixaAtual.querySelectorAll<HTMLElement>(FOCAVEIS));
      if (itens.length === 0) return;
      const a = itens[0];
      const z = itens[itens.length - 1];
      if (e.shiftKey && document.activeElement === a) {
        e.preventDefault();
        z.focus();
      } else if (!e.shiftKey && document.activeElement === z) {
        e.preventDefault();
        a.focus();
      }
    }
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("keydown", tecla);
      document.body.style.overflow = corpo;
      anterior?.focus?.();
    };
  }, []);

  return (
    <div className="modal-fundo" onMouseDown={(e) => e.target === e.currentTarget && aoFechar()}>
      <div
        ref={caixa}
        className={largo ? "modal modal--largo" : "modal"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
      >
        <header className="modal__cab">
          <h2 id={idTitulo}>{titulo}</h2>
          <button type="button" className="btn-icone" onClick={aoFechar} aria-label="Fechar">
            <X aria-hidden="true" />
          </button>
        </header>
        <div className="modal__corpo">{children}</div>
      </div>
    </div>
  );
}

interface ConfirmarProps {
  titulo: string;
  mensagem: ReactNode;
  rotuloConfirmar: string;
  perigo?: boolean;
  ocupado?: boolean;
  aoConfirmar: () => void;
  aoFechar: () => void;
}

export function Confirmar({ titulo, mensagem, rotuloConfirmar, perigo, ocupado, aoConfirmar, aoFechar }: ConfirmarProps) {
  return (
    <Modal titulo={titulo} aoFechar={aoFechar}>
      <div className="texto">{mensagem}</div>
      <div className="acoes">
        <button type="button" className="btn btn--sec" onClick={aoFechar} disabled={ocupado}>
          Voltar
        </button>
        <button
          type="button"
          className={perigo ? "btn btn--perigo" : "btn"}
          onClick={aoConfirmar}
          disabled={ocupado}
        >
          {ocupado ? "Aguarde…" : rotuloConfirmar}
        </button>
      </div>
    </Modal>
  );
}
