// Tipos espelham os DTOs de backend/src/manutencao/api/esquemas.py (o backend é a autoridade).
export type Papel = "Gestor" | "Técnico";
export type Disponibilidade = "Disponível" | "Em atendimento" | "Ausente";
export type Criticidade = "Baixa" | "Média" | "Alta" | "Crítica";
export type StatusOS =
  | "Aberta"
  | "Atribuída"
  | "Em Execução"
  | "Aguardando Peça"
  | "Reparo Finalizado"
  | "Aguardando Aprovação"
  | "Concluída"
  | "Cancelada";
export type TipoServico =
  | "Abertura"
  | "Atribuição"
  | "Reatribuição"
  | "Diagnóstico"
  | "Reparo"
  | "Mudança de status"
  | "Apontamento"
  | "Teste funcional"
  | "Conclusão técnica"
  | "Encerramento"
  | "Reprovação"
  | "Cancelamento";
export type Permissao =
  | "ver_equipamentos"
  | "ver_os"
  | "abrir_os"
  | "ver_disponibilidade"
  | "registrar_apontamento"
  | "diagnosticar"
  | "apontar_reparo"
  | "atualizar_status"
  | "concluir_os"
  | "gerir_equipamentos"
  | "gerir_usuarios"
  | "atribuir_os"
  | "aprovar_os";

export interface Pagina<T> {
  itens: T[];
  total: number;
  limite: number;
  deslocamento: number;
}
export interface CargoResumo {
  id: number;
  nome: string;
}
export interface Usuario {
  id: number;
  nome: string;
  email: string;
  escala: string;
  papel: Papel;
  ativo: boolean;
  disponibilidade: Disponibilidade;
  cargo: CargoResumo;
  permissoes: Permissao[];
}
export interface UsuarioAtual extends Usuario {
  login: string | null;
}
export interface Sessao {
  usuario: UsuarioAtual;
  csrf_token: string;
  expira_em: string;
}
export interface PermissaoInfo {
  nome: Permissao;
  descricao: string;
}
export interface Cargo {
  id: number;
  nome: string;
  permissoes: Permissao[];
}
export interface DisponibilidadeTecnico {
  id: number;
  nome: string;
  escala: string;
  disponibilidade: Disponibilidade;
  carga: number;
}
export interface Equipamento {
  id: number;
  nome: string;
  modelo: string;
  ativo: boolean;
  situacao: string;
}
export interface UsuarioResumo {
  id: number;
  nome: string;
}
export interface EquipamentoResumo {
  id: number;
  nome: string;
  modelo: string;
  ativo: boolean;
}
export interface Peca {
  descricao: string;
  quantidade: number;
}
export interface Ordem {
  numero: number;
  status: StatusOS;
  criticidade: Criticidade;
  falha: string;
  equipamento: EquipamentoResumo;
  aberta_por: UsuarioResumo;
  tecnico: UsuarioResumo | null;
  data_abertura: string;
  data_conclusao: string | null;
  diagnostico: string;
  causa_raiz: string;
  teste_funcional: string;
  motivo_cancelamento: string;
  horas_trabalhadas: number;
  intervencoes: string[];
  pecas: Peca[];
  encerrada: boolean;
}
export interface Servico {
  numero: number;
  tipo: TipoServico;
  descricao: string;
  responsavel: UsuarioResumo | null;
  data: string;
  horas: number;
  pecas: Peca[];
}
export interface Painel {
  total: number;
  em_aberto: number;
  encerradas: number;
  minhas_em_aberto: number;
  por_status: { status: StatusOS; quantidade: number }[];
  por_criticidade_em_aberto: { criticidade: Criticidade; quantidade: number }[];
  recentes: Ordem[];
  tecnicos: DisponibilidadeTecnico[] | null;
}
export interface FiltroOrdens {
  status?: StatusOS | "";
  criticidade?: Criticidade | "";
  equipamento_id?: number | "";
  tecnico_id?: number | "";
  encerrada?: "" | "true" | "false";
  mais_antigas_primeiro?: boolean;
  limite?: number;
  deslocamento?: number;
}
export interface DetalheDeCampo {
  campo: string;
  mensagem: string;
}
