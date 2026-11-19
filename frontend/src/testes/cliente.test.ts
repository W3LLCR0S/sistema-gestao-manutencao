import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErroApi, aoSessaoExpirar, api, definirCsrf, mensagemDeErro, montarConsulta } from "../api/cliente";

function resposta(status: number, corpo?: unknown): Response {
  return new Response(corpo === undefined ? null : JSON.stringify(corpo), { status });
}

describe("cliente HTTP", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    definirCsrf(null);
    aoSessaoExpirar(null);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("envia o token CSRF só em escritas e usa a mesma origem (cookie HttpOnly)", async () => {
    definirCsrf("token-123");
    fetchMock.mockImplementation(async () => resposta(200, {}));
    await api.get("/equipamentos");
    await api.post("/equipamentos", { nome: "a" });
    const [get, post] = fetchMock.mock.calls;
    expect(get[0]).toBe("/api/v1/equipamentos");
    expect(get[1].headers["X-CSRF-Token"]).toBeUndefined();
    expect(post[1].headers["X-CSRF-Token"]).toBe("token-123");
    expect(post[1].credentials).toBe("same-origin");
    expect(post[1].body).toBe(JSON.stringify({ nome: "a" }));
  });

  it("não grava nada em localStorage", async () => {
    definirCsrf("segredo");
    fetchMock.mockImplementation(async () => resposta(200, {}));
    await api.post("/x", {});
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("traduz erros da API preservando código e status", async () => {
    fetchMock.mockResolvedValue(resposta(409, { codigo: "ultimo_gestor", mensagem: "Último gestor." }));
    const erro = (await api.post("/usuarios/1/desativar").catch((e) => e)) as ErroApi;
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro.status).toBe(409);
    expect(erro.codigo).toBe("ultimo_gestor");
    expect(mensagemDeErro(erro)).toBe("Último gestor.");
  });

  it("mostra os campos de um 422 de validação", async () => {
    fetchMock.mockResolvedValue(
      resposta(422, { codigo: "entrada_invalida", mensagem: "Inválido", detalhes: [{ campo: "nome", mensagem: "obrigatório" }] }),
    );
    const erro = (await api.post("/usuarios", {}).catch((e) => e)) as ErroApi;
    expect(mensagemDeErro(erro)).toBe("nome: obrigatório");
  });

  it("401 aciona o retorno ao login, exceto quando pedido", async () => {
    const expirou = vi.fn();
    aoSessaoExpirar(expirou);
    fetchMock.mockResolvedValue(resposta(401, { codigo: "nao_autenticado", mensagem: "x" }));
    await api.get("/ordens").catch(() => undefined);
    expect(expirou).toHaveBeenCalledTimes(1);
    await api.post("/auth/login", {}, { semRedirecionar: true }).catch(() => undefined);
    expect(expirou).toHaveBeenCalledTimes(1);
  });

  it("falha de rede vira ErroApi com status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const erro = (await api.get("/ordens").catch((e) => e)) as ErroApi;
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro.status).toBe(0);
    expect(erro.codigo).toBe("sem_conexao");
  });

  it("204 e corpo inválido não quebram", async () => {
    fetchMock.mockResolvedValueOnce(resposta(204));
    await expect(api.delete("/equipamentos/1")).resolves.toBeUndefined();
    fetchMock.mockResolvedValueOnce(new Response("<html>502</html>", { status: 502 }));
    const erro = (await api.get("/x").catch((e) => e)) as ErroApi;
    expect(erro.status).toBe(502);
  });

  it("monta a consulta ignorando valores vazios", () => {
    expect(montarConsulta({ status: "Aberta", criticidade: "", equipamento_id: undefined, limite: 10 })).toBe(
      "?status=Aberta&limite=10",
    );
    expect(montarConsulta({})).toBe("");
  });
});
