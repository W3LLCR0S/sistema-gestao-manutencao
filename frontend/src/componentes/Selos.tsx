import type { Criticidade, Disponibilidade, StatusOS } from "../api/tipos";

const CLASSE_STATUS: Record<StatusOS, string> = {
  Aberta: "azul",
  Atribuída: "indigo",
  "Em Execução": "ambar",
  "Aguardando Peça": "laranja",
  "Reparo Finalizado": "ciano",
  "Aguardando Aprovação": "roxo",
  Concluída: "verde",
  Cancelada: "cinza",
};
const CLASSE_CRIT: Record<Criticidade, string> = {
  Baixa: "verde",
  Média: "ambar",
  Alta: "laranja",
  Crítica: "vermelho",
};
const CLASSE_DISP: Record<Disponibilidade, string> = {
  Disponível: "verde",
  "Em atendimento": "ambar",
  Ausente: "cinza",
};

// Texto sempre presente: a cor nunca é o único indicador (acessibilidade).
export function SeloStatus({ status }: { status: StatusOS }) {
  return <span className={`selo selo--${CLASSE_STATUS[status]}`}>{status}</span>;
}
export function SeloCriticidade({ criticidade }: { criticidade: Criticidade }) {
  return <span className={`selo selo--${CLASSE_CRIT[criticidade]}`}>{criticidade}</span>;
}
export function SeloDisponibilidade({ valor }: { valor: Disponibilidade }) {
  return <span className={`selo selo--${CLASSE_DISP[valor]}`}>{valor}</span>;
}
export function SeloAtivo({ ativo }: { ativo: boolean }) {
  return <span className={`selo selo--${ativo ? "verde" : "cinza"}`}>{ativo ? "Ativo" : "Inativo"}</span>;
}
