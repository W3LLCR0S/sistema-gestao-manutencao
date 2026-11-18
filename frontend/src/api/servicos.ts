import { api } from "./cliente";
import type {
  Cargo,
  Criticidade,
  Disponibilidade,
  DisponibilidadeTecnico,
  Equipamento,
  FiltroOrdens,
  Ordem,
  Pagina,
  Painel,
  Papel,
  Peca,
  Permissao,
  PermissaoInfo,
  Servico,
  Sessao,
  StatusOS,
  Usuario,
  UsuarioResumo,
} from "./tipos";

export const autenticacao = {
  login: (login: string, senha: string) =>
    api.post<Sessao>("/auth/login", { login, senha }, { semRedirecionar: true }),
  logout: () => api.post<void>("/auth/logout", {}, { semRedirecionar: true }),
  eu: () => api.get<Sessao>("/auth/me"),
  alterarSenha: (senha_atual: string, nova_senha: string) =>
    api.post<void>("/auth/alterar-senha", { senha_atual, nova_senha }),
};

export interface NovoUsuario {
  nome: string;
  cargo_id: number;
  papel: Papel;
  email?: string;
  escala?: string;
  login?: string;
  senha?: string;
}

export const usuarios = {
  listar: (ativo?: boolean, papel?: Papel) =>
    api.get<Pagina<Usuario>>("/usuarios", { ativo, papel, limite: 200 }),
  obter: (id: number) => api.get<Usuario>(`/usuarios/${id}`),
  criar: (u: NovoUsuario) => api.post<Usuario>("/usuarios", u),
  atualizar: (id: number, d: { nome?: string; email?: string; escala?: string }) =>
    api.patch<Usuario>(`/usuarios/${id}`, d),
  alterarCargo: (id: number, cargo_id: number) =>
    api.put<Usuario>(`/usuarios/${id}/cargo`, { cargo_id }),
  alterarPapel: (id: number, papel: Papel) => api.put<Usuario>(`/usuarios/${id}/papel`, { papel }),
  desativar: (id: number) => api.post<Usuario>(`/usuarios/${id}/desativar`),
  reativar: (id: number) => api.post<Usuario>(`/usuarios/${id}/reativar`),
  excluir: (id: number) => api.delete<void>(`/usuarios/${id}`),
  definirCredencial: (id: number, login: string, senha: string) =>
    api.put<Usuario>(`/usuarios/${id}/credencial`, { login, senha }),
  alterarDisponibilidade: (id: number, disponibilidade: Disponibilidade) =>
    api.put<Usuario>(`/usuarios/${id}/disponibilidade`, { disponibilidade }),
  minhaDisponibilidade: (disponibilidade: Disponibilidade) =>
    api.put<Usuario>("/me/disponibilidade", { disponibilidade }),
};

export const cargos = {
  listar: () => api.get<Cargo[]>("/cargos"),
  definirPermissoes: (id: number, permissoes: Permissao[]) =>
    api.put<Cargo>(`/cargos/${id}/permissoes`, { permissoes }),
  catalogo: () => api.get<PermissaoInfo[]>("/permissoes"),
};

export const disponibilidade = {
  listar: (ordenar_por_carga = false) =>
    api.get<DisponibilidadeTecnico[]>("/disponibilidade", { ordenar_por_carga }),
};

export const equipamentos = {
  listar: (apenas_ativos = false) =>
    api.get<Pagina<Equipamento>>("/equipamentos", { apenas_ativos, limite: 200 }),
  obter: (id: number) => api.get<Equipamento>(`/equipamentos/${id}`),
  criar: (d: { nome: string; modelo: string }) => api.post<Equipamento>("/equipamentos", d),
  atualizar: (id: number, d: { nome: string; modelo: string }) =>
    api.put<Equipamento>(`/equipamentos/${id}`, d),
  excluir: (id: number) => api.delete<void>(`/equipamentos/${id}`),
  inativar: (id: number) => api.post<Equipamento>(`/equipamentos/${id}/inativar`),
  reativar: (id: number) => api.post<Equipamento>(`/equipamentos/${id}/reativar`),
};

export const ordens = {
  listar: (f: FiltroOrdens = {}) => api.get<Pagina<Ordem>>("/ordens", { limite: 200, ...f }),
  obter: (n: number) => api.get<Ordem>(`/ordens/${n}`),
  historico: (n: number) => api.get<Servico[]>(`/ordens/${n}/historico`),
  abrir: (d: { equipamento_id: number; falha: string; criticidade: Criticidade }) =>
    api.post<Ordem>("/ordens", d),
  diagnosticar: (n: number, parecer: string, causa_raiz: string) =>
    api.post<Ordem>(`/ordens/${n}/diagnostico`, { parecer, causa_raiz }),
  apontarReparo: (n: number, d: { horas: number; intervencao: string; pecas: Peca[] }) =>
    api.post<Ordem>(`/ordens/${n}/reparos`, d),
  alterarStatus: (n: number, status: StatusOS) =>
    api.post<Ordem>(`/ordens/${n}/status`, { status }),
  concluirTecnicamente: (n: number, teste: string, passou: boolean) =>
    api.post<{ submetida_a_aprovacao: boolean; ordem: Ordem }>(`/ordens/${n}/conclusao-tecnica`, {
      teste,
      passou,
    }),
  apontamento: (n: number, texto: string) =>
    api.post<Ordem>(`/ordens/${n}/apontamentos`, { texto }),
  atribuir: (n: number, tecnico_id: number, confirmar_ausente = false) =>
    api.post<{ ordem: Ordem; tecnico_anterior: UsuarioResumo | null }>(`/ordens/${n}/atribuicao`, {
      tecnico_id,
      confirmar_ausente,
    }),
  aprovar: (n: number) => api.post<Ordem>(`/ordens/${n}/aprovacao`),
  reprovar: (n: number, motivo: string) => api.post<Ordem>(`/ordens/${n}/reprovacao`, { motivo }),
  cancelar: (n: number, motivo: string) => api.post<Ordem>(`/ordens/${n}/cancelamento`, { motivo }),
};

export const painel = { obter: () => api.get<Painel>("/painel") };
