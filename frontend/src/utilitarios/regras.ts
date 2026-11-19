// Orientação da interface. O BACKEND continua sendo a autoridade: estas funções só decidem
// quais botões mostrar; qualquer ação indevida ainda é recusada pela API (403/409/422).
import type { Ordem, Permissao, StatusOS, UsuarioAtual } from "../api/tipos";

export const ATENDIMENTO: StatusOS[] = ["Atribuída", "Em Execução", "Aguardando Peça"];
export const STATUS_DO_TECNICO: StatusOS[] = ["Em Execução", "Aguardando Peça", "Reparo Finalizado"];
const ORIGEM_DO_TECNICO: StatusOS[] = ["Atribuída", ...STATUS_DO_TECNICO];

export const TODOS_STATUS: StatusOS[] = [
  "Aberta",
  "Atribuída",
  "Em Execução",
  "Aguardando Peça",
  "Reparo Finalizado",
  "Aguardando Aprovação",
  "Concluída",
  "Cancelada",
];

export function tem(usuario: UsuarioAtual | null | undefined, p: Permissao): boolean {
  return !!usuario && usuario.ativo && usuario.permissoes.includes(p);
}

export interface Acoes {
  diagnosticar: boolean;
  reparo: boolean;
  statusPossiveis: StatusOS[];
  concluir: boolean;
  atribuir: boolean;
  aprovar: boolean;
  cancelar: boolean;
  apontamento: boolean;
}

export function acoesDisponiveis(o: Ordem, u: UsuarioAtual | null): Acoes {
  const vazio: Acoes = {
    diagnosticar: false,
    reparo: false,
    statusPossiveis: [],
    concluir: false,
    atribuir: false,
    aprovar: false,
    cancelar: false,
    apontamento: false,
  };
  if (!u) return vazio;
  const responsavel = o.tecnico?.id === u.id;
  return {
    diagnosticar: tem(u, "diagnosticar") && responsavel && ATENDIMENTO.includes(o.status),
    reparo: tem(u, "apontar_reparo") && responsavel && ATENDIMENTO.includes(o.status),
    statusPossiveis:
      tem(u, "atualizar_status") && responsavel && ORIGEM_DO_TECNICO.includes(o.status)
        ? STATUS_DO_TECNICO.filter((s) => s !== o.status)
        : [],
    concluir: tem(u, "concluir_os") && responsavel && o.status === "Reparo Finalizado",
    atribuir: tem(u, "atribuir_os") && !o.encerrada && o.status !== "Aguardando Aprovação",
    aprovar: tem(u, "aprovar_os") && o.status === "Aguardando Aprovação",
    cancelar: tem(u, "aprovar_os") && !o.encerrada,
    apontamento: tem(u, "registrar_apontamento") && !o.encerrada,
  };
}

export const ROTULO_PERMISSAO: Record<Permissao, string> = {
  ver_equipamentos: "Ver equipamentos",
  ver_os: "Consultar OS",
  abrir_os: "Abrir OS",
  ver_disponibilidade: "Ver disponibilidade",
  registrar_apontamento: "Registrar apontamentos",
  diagnosticar: "Diagnosticar",
  apontar_reparo: "Apontar reparo",
  atualizar_status: "Atualizar status",
  concluir_os: "Concluir tecnicamente",
  gerir_equipamentos: "Gerir equipamentos",
  gerir_usuarios: "Gerir usuários",
  atribuir_os: "Atribuir OS",
  aprovar_os: "Aprovar/cancelar OS",
};
