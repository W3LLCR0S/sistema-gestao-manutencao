import { describe, expect, it } from "vitest";
import type { Ordem, Permissao, StatusOS, UsuarioAtual } from "../api/tipos";
import { dataHora, horas, lerNumero, numeroOS } from "../utilitarios/formatar";
import { acoesDisponiveis } from "../utilitarios/regras";

const TECNICO_PERMS: Permissao[] = [
  "ver_equipamentos", "ver_os", "abrir_os", "ver_disponibilidade", "registrar_apontamento",
  "diagnosticar", "apontar_reparo", "atualizar_status", "concluir_os",
];
const GESTOR_PERMS: Permissao[] = [
  "ver_equipamentos", "ver_os", "abrir_os", "ver_disponibilidade", "registrar_apontamento",
  "gerir_equipamentos", "gerir_usuarios", "atribuir_os", "aprovar_os",
];

function usuario(id: number, papel: "Gestor" | "Técnico", permissoes: Permissao[], ativo = true): UsuarioAtual {
  return {
    id, nome: "U", email: "", escala: "", papel, ativo, disponibilidade: "Disponível",
    cargo: { id: 1, nome: "C" }, permissoes, login: "u",
  };
}
function ordem(status: StatusOS, tecnicoId: number | null = 2): Ordem {
  return {
    numero: 1, status, criticidade: "Alta", falha: "f",
    equipamento: { id: 1, nome: "E", modelo: "M", ativo: true },
    aberta_por: { id: 1, nome: "G" },
    tecnico: tecnicoId === null ? null : { id: tecnicoId, nome: "T" },
    data_abertura: "2026-11-17T12:00:00Z", data_conclusao: null, diagnostico: "", causa_raiz: "",
    teste_funcional: "", motivo_cancelamento: "", horas_trabalhadas: 0, intervencoes: [], pecas: [],
    encerrada: status === "Concluída" || status === "Cancelada",
  };
}

describe("ações disponíveis na OS (orientação; o backend decide)", () => {
  const gestor = usuario(1, "Gestor", GESTOR_PERMS);
  const tecnico = usuario(2, "Técnico", TECNICO_PERMS);
  const outroTecnico = usuario(3, "Técnico", TECNICO_PERMS);

  it("técnico responsável executa; outro técnico não", () => {
    const a = acoesDisponiveis(ordem("Em Execução"), tecnico);
    expect(a.diagnosticar && a.reparo).toBe(true);
    expect(a.statusPossiveis).toEqual(["Aguardando Peça", "Reparo Finalizado"]);
    const b = acoesDisponiveis(ordem("Em Execução"), outroTecnico);
    expect(b.diagnosticar || b.reparo || b.concluir).toBe(false);
    expect(b.statusPossiveis).toEqual([]);
  });

  it("técnico não atribui, aprova nem cancela", () => {
    const a = acoesDisponiveis(ordem("Aguardando Aprovação"), tecnico);
    expect(a.atribuir || a.aprovar || a.cancelar).toBe(false);
  });

  it("gestor atribui e cancela, mas não executa a OS de um técnico", () => {
    const a = acoesDisponiveis(ordem("Aberta", null), gestor);
    expect(a.atribuir && a.cancelar).toBe(true);
    expect(a.diagnosticar || a.reparo || a.concluir).toBe(false);
  });

  it("aprovação só em 'Aguardando Aprovação', e sem atribuir nesse estado", () => {
    const a = acoesDisponiveis(ordem("Aguardando Aprovação"), gestor);
    expect(a.aprovar).toBe(true);
    expect(a.atribuir).toBe(false);
  });

  it("conclusão técnica só em 'Reparo Finalizado'", () => {
    expect(acoesDisponiveis(ordem("Reparo Finalizado"), tecnico).concluir).toBe(true);
    expect(acoesDisponiveis(ordem("Em Execução"), tecnico).concluir).toBe(false);
  });

  it("OS encerrada não oferece ações", () => {
    for (const s of ["Concluída", "Cancelada"] as StatusOS[]) {
      const a = acoesDisponiveis(ordem(s), gestor);
      expect(a.atribuir || a.cancelar || a.aprovar || a.apontamento).toBe(false);
    }
  });

  it("usuário inativo não tem ação alguma", () => {
    const a = acoesDisponiveis(ordem("Em Execução"), usuario(2, "Técnico", TECNICO_PERMS, false));
    expect(a.diagnosticar || a.reparo || a.apontamento).toBe(false);
  });
});

describe("formatação", () => {
  it("converte UTC para America/Sao_Paulo", () => {
    expect(dataHora("2026-11-17T15:30:00Z")).toContain("12:30");
  });
  it("trata ausência de data", () => {
    expect(dataHora(null)).toBe("—");
    expect(dataHora("lixo")).toBe("—");
  });
  it("numera OS e formata horas", () => {
    expect(numeroOS(7)).toBe("OS #0007");
    expect(horas(1.5)).toBe("1,5 h");
  });
  it("lê números com vírgula e recusa texto", () => {
    expect(lerNumero("1,5")).toBe(1.5);
    expect(lerNumero("2.25")).toBe(2.25);
    expect(Number.isNaN(lerNumero(""))).toBe(true);
    expect(Number.isNaN(lerNumero("abc"))).toBe(true);
  });
});
