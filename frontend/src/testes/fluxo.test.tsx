import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Aplicacao } from "../Aplicacao";
import { ProvedorAutenticacao } from "../auth/Autenticacao";
import { ProvedorAvisos } from "../componentes/Avisos";
import { definirCsrf } from "../api/cliente";
import type { Permissao, Sessao } from "../api/tipos";

const PERMS_TECNICO: Permissao[] = ["ver_equipamentos", "ver_os", "abrir_os", "ver_disponibilidade", "registrar_apontamento", "diagnosticar", "apontar_reparo", "atualizar_status", "concluir_os"];
const PERMS_GESTOR: Permissao[] = ["ver_equipamentos", "ver_os", "abrir_os", "ver_disponibilidade", "registrar_apontamento", "gerir_equipamentos", "gerir_usuarios", "atribuir_os", "aprovar_os"];

function sessao(papel: "Gestor" | "Técnico"): Sessao {
  return {
    csrf_token: "csrf-teste",
    expira_em: "2026-11-18T20:00:00Z",
    usuario: {
      id: 1, nome: papel === "Gestor" ? "Gina Gestora" : "Tom Técnico", email: "", escala: "", papel,
      ativo: true, disponibilidade: "Disponível", cargo: { id: 1, nome: papel },
      permissoes: papel === "Gestor" ? PERMS_GESTOR : PERMS_TECNICO, login: "u",
    },
  };
}
const painelVazio = { total: 0, em_aberto: 0, encerradas: 0, minhas_em_aberto: 0, por_status: [], por_criticidade_em_aberto: [], recentes: [], tecnicos: null };

/** Servidor falso na fronteira do fetch: só para testar componentes; o fluxo real é o E2E com a API. */
function servidor(opcoes: { logado?: "Gestor" | "Técnico" | null; loginOk?: boolean }) {
  let logado = opcoes.logado ?? null;
  const chamadas: { metodo: string; url: string; csrf?: string }[] = [];
  const mock = vi.fn(async (url: string, init?: RequestInit) => {
    const metodo = init?.method ?? "GET";
    const cab = (init?.headers ?? {}) as Record<string, string>;
    chamadas.push({ metodo, url, csrf: cab["X-CSRF-Token"] });
    const json = (s: number, c: unknown) => new Response(JSON.stringify(c), { status: s });
    if (url === "/api/v1/auth/me") return logado ? json(200, sessao(logado)) : json(401, { codigo: "nao_autenticado", mensagem: "Faça login." });
    if (url === "/api/v1/auth/login") {
      if (opcoes.loginOk === false) return json(401, { codigo: "credenciais_invalidas", mensagem: "Credenciais inválidas." });
      logado = "Gestor";
      return json(200, sessao("Gestor"));
    }
    if (url === "/api/v1/auth/logout") {
      logado = null;
      return new Response(null, { status: 204 });
    }
    if (url === "/api/v1/painel") return json(200, painelVazio);
    if (url.startsWith("/api/v1/ordens")) return json(200, { itens: [], total: 0, limite: 100, deslocamento: 0 });
    if (url.startsWith("/api/v1/equipamentos")) return json(200, { itens: [], total: 0, limite: 100, deslocamento: 0 });
    return json(404, { codigo: "rota_nao_encontrada", mensagem: "?" });
  });
  vi.stubGlobal("fetch", mock);
  return { chamadas };
}

function montar(rota: string) {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <ProvedorAvisos>
        <ProvedorAutenticacao>
          <Aplicacao />
        </ProvedorAutenticacao>
      </ProvedorAvisos>
    </MemoryRouter>,
  );
}

describe("fluxos de tela", () => {
  beforeEach(() => definirCsrf(null));
  afterEach(() => vi.unstubAllGlobals());

  it("sem sessão, uma rota protegida leva ao login", async () => {
    servidor({ logado: null });
    montar("/ordens");
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("login correto abre o painel com dados da API", async () => {
    servidor({ logado: null });
    montar("/");
    await userEvent.type(await screen.findByLabelText("Usuário"), "gina");
    await userEvent.type(screen.getByLabelText("Senha"), "segredo");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("heading", { name: "Painel" })).toBeInTheDocument();
    expect(screen.getByText(/Gina Gestora/, { selector: ".pagina-cab__sub" })).toBeInTheDocument();
  });

  it("senha errada mostra o erro e limpa a senha", async () => {
    servidor({ logado: null, loginOk: false });
    montar("/login");
    await userEvent.type(await screen.findByLabelText("Usuário"), "gina");
    await userEvent.type(screen.getByLabelText("Senha"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Usuário ou senha incorretos.");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("login exige usuário e senha antes de chamar a API", async () => {
    const { chamadas } = servidor({ logado: null });
    montar("/login");
    await userEvent.click(await screen.findByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Informe o usuário e a senha.");
    expect(chamadas.some((c) => c.url.endsWith("/auth/login"))).toBe(false);
  });

  it("técnico não vê Usuários/Cargos no menu e é barrado na URL", async () => {
    servidor({ logado: "Técnico" });
    montar("/usuarios");
    expect(await screen.findByRole("heading", { name: "Acesso negado" })).toBeInTheDocument();
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).queryByText("Usuários")).not.toBeInTheDocument();
    expect(within(menu).getByText("Ordens de serviço")).toBeInTheDocument();
  });

  it("gestor vê a administração no menu", async () => {
    servidor({ logado: "Gestor" });
    montar("/");
    const menu = await screen.findByRole("navigation", { name: "Principal" });
    expect(within(menu).getByText("Usuários")).toBeInTheDocument();
    expect(within(menu).getByText("Cargos e permissões")).toBeInTheDocument();
  });

  it("sair encerra a sessão no servidor e volta ao login", async () => {
    const { chamadas } = servidor({ logado: "Gestor" });
    montar("/");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    const saida = chamadas.find((c) => c.url.endsWith("/auth/logout"));
    expect(saida?.metodo).toBe("POST");
    expect(saida?.csrf).toBe("csrf-teste");
  });

  it("formulário de equipamento valida antes de enviar", async () => {
    const { chamadas } = servidor({ logado: "Gestor" });
    montar("/equipamentos");
    await userEvent.click(await screen.findByRole("button", { name: /Novo equipamento/ }));
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Salvar" }));
    expect(await within(dialogo).findByRole("alert")).toHaveTextContent("Informe o nome e o modelo.");
    await waitFor(() => expect(chamadas.filter((c) => c.metodo === "POST" && c.url.endsWith("/equipamentos"))).toHaveLength(0));
  });
});
