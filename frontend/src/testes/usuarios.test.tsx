import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Aplicacao } from "../Aplicacao";
import { definirCsrf } from "../api/cliente";
import type { Permissao, Usuario } from "../api/tipos";
import { ProvedorAutenticacao } from "../auth/Autenticacao";
import { ProvedorAvisos } from "../componentes/Avisos";
import { matriculaValida, normalizarDigitacaoDaMatricula } from "../utilitarios/matricula";

const PERMS: Permissao[] = ["ver_equipamentos", "ver_os", "gerir_usuarios", "atribuir_os", "aprovar_os"];

function usuario(id: number, nome: string, matricula: string, papel: "Gestor" | "Técnico" = "Técnico"): Usuario {
  return {
    id, matricula, nome, email: `${nome.toLowerCase()}@x.com`, escala: "", papel, ativo: true,
    disponibilidade: "Disponível", cargo: { id: 2, nome: papel }, permissoes: PERMS,
  };
}
const ANA = usuario(1, "Ana", "KM482731", "Gestor");
const BRUNO = usuario(2, "Bruno", "RT095624");
const CARLA = usuario(3, "Carla", "VX716309");
const DIEGO = usuario(4, "Diego", "QW123456");

function servidor() {
  const chamadas: { metodo: string; url: string; corpo?: Record<string, unknown> }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const metodo = init?.method ?? "GET";
      const corpo = typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : undefined;
      chamadas.push({ metodo, url, corpo });
      const json = (s: number, c: unknown) => new Response(JSON.stringify(c), { status: s });
      if (url === "/api/v1/auth/me") return json(200, { usuario: ANA, csrf_token: "csrf", expira_em: "2026-11-18T20:00:00Z" });
      if (url === "/api/v1/cargos") return json(200, [{ id: 2, nome: "Técnico", permissoes: [] }]);
      if (url.startsWith("/api/v1/usuarios") && metodo === "POST") return json(201, DIEGO);
      if (url.startsWith("/api/v1/usuarios")) {
        const busca = new URL(url, "http://x").searchParams.get("busca")?.toLowerCase();
        const todos = [ANA, BRUNO, CARLA];
        const itens = busca ? todos.filter((u) => u.matricula.toLowerCase().includes(busca) || u.nome.toLowerCase().includes(busca)) : todos;
        return json(200, { itens, total: itens.length, limite: 200, deslocamento: 0 });
      }
      return json(404, { codigo: "rota_nao_encontrada", mensagem: "?" });
    }),
  );
  return { chamadas };
}

function montar() {
  return render(
    <MemoryRouter initialEntries={["/usuarios"]}>
      <ProvedorAvisos>
        <ProvedorAutenticacao>
          <Aplicacao />
        </ProvedorAutenticacao>
      </ProvedorAvisos>
    </MemoryRouter>,
  );
}

describe("matrícula: utilitários", () => {
  it("valida o formato AA999999", () => {
    for (const ok of ["KM482731", "AA000000", "ZZ999999"]) expect(matriculaValida(ok)).toBe(true);
    for (const ruim of ["", "ana", "km482731", "KM48273", "KM4827311", "K1482731", "KMA82731", " KM482731"]) {
      expect(matriculaValida(ruim)).toBe(false);
    }
  });
  it("normaliza a digitação", () => {
    expect(normalizarDigitacaoDaMatricula("km-48 2731999")).toBe("KM482731");
    expect(normalizarDigitacaoDaMatricula("ç!@")).toBe("");
  });
});

describe("usuários e matrícula", () => {
  beforeEach(() => definirCsrf(null));
  afterEach(() => vi.unstubAllGlobals());

  it("a listagem mostra a matrícula de cada usuário", async () => {
    servidor();
    montar();
    const tabela = await screen.findByRole("table");
    for (const u of [ANA, BRUNO, CARLA]) expect(within(tabela).getByText(u.matricula)).toBeInTheDocument();
    expect(within(tabela).getByRole("columnheader", { name: "Matrícula" })).toBeInTheDocument();
  });

  it("os detalhes mostram a matrícula", async () => {
    servidor();
    montar();
    await userEvent.click((await screen.findAllByRole("button", { name: "Detalhes" }))[1]);
    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByText("RT095624")).toBeInTheDocument();
    expect(within(dialogo).getByText("Matrícula")).toBeInTheDocument();
  });

  it("pesquisar por matrícula consulta o servidor com o termo", async () => {
    const { chamadas } = servidor();
    montar();
    await screen.findByRole("table");
    await userEvent.type(screen.getByLabelText(/Buscar por matrícula/), "vx7163");
    await waitFor(() => expect(chamadas.some((c) => c.url.includes("busca=vx7163"))).toBe(true));
    await waitFor(() => expect(screen.queryByText("RT095624")).not.toBeInTheDocument());
    expect(screen.getByText("VX716309")).toBeInTheDocument();
  });

  it("cadastrar não envia matrícula e exibe a matrícula gerada na confirmação", async () => {
    const { chamadas } = servidor();
    montar();
    await userEvent.click(await screen.findByRole("button", { name: /Novo usuário/ }));
    const form = await screen.findByRole("dialog");
    expect(within(form).queryByLabelText(/login/i)).not.toBeInTheDocument();
    expect(within(form).getByText(/matrícula .* é gerada automaticamente/i)).toBeInTheDocument();
    await userEvent.type(within(form).getByLabelText("Nome"), "Diego");
    await userEvent.click(within(form).getByRole("button", { name: "Cadastrar" }));
    const envio = chamadas.find((c) => c.metodo === "POST" && c.url === "/api/v1/usuarios");
    expect(envio?.corpo).toBeDefined();
    expect(envio?.corpo).not.toHaveProperty("matricula");
    expect(envio?.corpo).not.toHaveProperty("login");
    const confirmacao = await screen.findByRole("dialog", { name: /Usuário cadastrado/ });
    expect(within(confirmacao).getByLabelText("Matrícula gerada")).toHaveTextContent("QW123456");
  });
});
