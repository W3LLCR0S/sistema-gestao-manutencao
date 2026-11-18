// A API entrega instantes em UTC (D-11); a interface exibe em America/Sao_Paulo.
const FUSO = "America/Sao_Paulo";

const fmtDataHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const fmtData = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

export function dataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : fmtDataHora.format(d);
}

export function soData(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : fmtData.format(d);
}

export function horas(h: number): string {
  return `${h.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} h`;
}

export function numeroOS(n: number): string {
  return `OS #${String(n).padStart(4, "0")}`;
}

/** Aceita "1,5" e "1.5"; devolve NaN se não for número finito. */
export function lerNumero(texto: string): number {
  const n = Number(texto.trim().replace(",", "."));
  return texto.trim() !== "" && Number.isFinite(n) ? n : Number.NaN;
}
