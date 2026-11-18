import { useState, type FormEvent, type ReactNode } from "react";
import { mensagemDeErro } from "../api/cliente";
import { Alerta } from "./Estados";
import { Modal } from "./Modal";

interface Props {
  titulo: string;
  rotuloEnviar: string;
  aoFechar: () => void;
  /** Lança erro (ErroApi) para exibir a mensagem do backend sem fechar o diálogo. */
  aoEnviar: () => Promise<void>;
  children: ReactNode;
  perigo?: boolean;
  largo?: boolean;
  /** Validação local rápida; devolve a mensagem de erro ou null. */
  validar?: () => string | null;
}

/** Diálogo com formulário: controla "enviando", exibe erros da API e fecha só em caso de sucesso. */
export function FormModal({ titulo, rotuloEnviar, aoFechar, aoEnviar, children, perigo, largo, validar }: Props) {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (enviando) return;
    const local = validar?.() ?? null;
    if (local) {
      setErro(local);
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await aoEnviar();
      aoFechar();
    } catch (ex) {
      setErro(mensagemDeErro(ex));
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={titulo} aoFechar={aoFechar} largo={largo}>
      <form onSubmit={enviar} noValidate>
        {erro && <Alerta>{erro}</Alerta>}
        {children}
        <div className="acoes">
          <button type="button" className="btn btn--sec" onClick={aoFechar} disabled={enviando}>
            Cancelar
          </button>
          <button type="submit" className={perigo ? "btn btn--perigo" : "btn"} disabled={enviando}>
            {enviando ? "Enviando…" : rotuloEnviar}
          </button>
        </div>
      </form>
    </Modal>
  );
}
