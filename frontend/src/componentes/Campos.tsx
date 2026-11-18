import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface Base {
  rotulo: string;
  ajuda?: string;
  erro?: string;
}

function Envoltorio({ id, rotulo, ajuda, erro, children }: Base & { id: string; children: ReactNode }) {
  return (
    <div className={erro ? "campo campo--erro" : "campo"}>
      <label htmlFor={id}>{rotulo}</label>
      {children}
      {ajuda && !erro && (
        <p className="campo__ajuda" id={`${id}-ajuda`}>
          {ajuda}
        </p>
      )}
      {erro && (
        <p className="campo__erro" id={`${id}-erro`}>
          {erro}
        </p>
      )}
    </div>
  );
}

function descrito(id: string, ajuda?: string, erro?: string) {
  return erro ? `${id}-erro` : ajuda ? `${id}-ajuda` : undefined;
}

export function CampoTexto({ rotulo, ajuda, erro, ...p }: Base & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} rotulo={rotulo} ajuda={ajuda} erro={erro}>
      <input id={id} aria-invalid={!!erro} aria-describedby={descrito(id, ajuda, erro)} {...p} />
    </Envoltorio>
  );
}

export function CampoAreaTexto({ rotulo, ajuda, erro, ...p }: Base & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} rotulo={rotulo} ajuda={ajuda} erro={erro}>
      <textarea id={id} rows={4} aria-invalid={!!erro} aria-describedby={descrito(id, ajuda, erro)} {...p} />
    </Envoltorio>
  );
}

export function CampoSelecao({
  rotulo,
  ajuda,
  erro,
  children,
  ...p
}: Base & SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  const id = useId();
  return (
    <Envoltorio id={id} rotulo={rotulo} ajuda={ajuda} erro={erro}>
      <select id={id} aria-invalid={!!erro} aria-describedby={descrito(id, ajuda, erro)} {...p}>
        {children}
      </select>
    </Envoltorio>
  );
}
