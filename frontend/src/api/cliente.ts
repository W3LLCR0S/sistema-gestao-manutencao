import type { DetalheDeCampo } from "./tipos";

const BASE = "/api/v1";

/** Erro da API: `codigo` estável do backend + status HTTP. `status === 0` = falha de rede. */
export class ErroApi extends Error {
  readonly status: number;
  readonly codigo: string;
  readonly detalhes: DetalheDeCampo[];
  constructor(status: number, codigo: string, mensagem: string, detalhes: DetalheDeCampo[] = []) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
    this.codigo = codigo;
    this.detalhes = detalhes;
  }
}

// O token CSRF fica só em memória (nunca em localStorage); /auth/me o devolve de novo após recarregar.
let tokenCsrf: string | null = null;
let aoExpirar: (() => void) | null = null;

export function definirCsrf(token: string | null): void {
  tokenCsrf = token;
}
export function aoSessaoExpirar(callback: (() => void) | null): void {
  aoExpirar = callback;
}

type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type Consulta = Record<string, string | number | boolean | null | undefined>;

export function montarConsulta(consulta?: Consulta): string {
  if (!consulta) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(consulta)) {
    if (v === undefined || v === null || v === "") continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export interface Opcoes {
  corpo?: unknown;
  consulta?: Consulta;
  /** 401 não dispara o redirecionamento ao login (usado no login e na verificação de sessão). */
  semRedirecionar?: boolean;
  sinal?: AbortSignal;
}

export async function requisitar<T>(metodo: Metodo, caminho: string, op: Opcoes = {}): Promise<T> {
  const cabecalhos: Record<string, string> = { Accept: "application/json" };
  if (metodo !== "GET" && tokenCsrf) cabecalhos["X-CSRF-Token"] = tokenCsrf;
  let corpo: string | undefined;
  if (op.corpo !== undefined) {
    cabecalhos["Content-Type"] = "application/json";
    corpo = JSON.stringify(op.corpo);
  }
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}${montarConsulta(op.consulta)}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo,
      credentials: "same-origin",
      signal: op.sinal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ErroApi(
      0,
      "sem_conexao",
      "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.",
    );
  }
  if (resposta.status === 204) return undefined as T;
  let dados: unknown = null;
  const texto = await resposta.text();
  if (texto) {
    try {
      dados = JSON.parse(texto);
    } catch {
      dados = null;
    }
  }
  if (!resposta.ok) {
    const e = (dados ?? {}) as { codigo?: string; mensagem?: string; detalhes?: DetalheDeCampo[] };
    const erro = new ErroApi(
      resposta.status,
      e.codigo ?? "erro",
      e.mensagem ?? `Erro ${resposta.status} ao falar com o servidor.`,
      e.detalhes ?? [],
    );
    if (resposta.status === 401 && !op.semRedirecionar && aoExpirar) aoExpirar();
    throw erro;
  }
  return dados as T;
}

export const api = {
  get: <T>(c: string, consulta?: Consulta, sinal?: AbortSignal) =>
    requisitar<T>("GET", c, { consulta, sinal }),
  post: <T>(c: string, corpo?: unknown, op?: Opcoes) =>
    requisitar<T>("POST", c, { corpo: corpo ?? {}, ...op }),
  put: <T>(c: string, corpo: unknown) => requisitar<T>("PUT", c, { corpo }),
  patch: <T>(c: string, corpo: unknown) => requisitar<T>("PATCH", c, { corpo }),
  delete: <T>(c: string) => requisitar<T>("DELETE", c),
};

/** Mensagem amigável para o usuário a partir de qualquer erro. */
export function mensagemDeErro(e: unknown): string {
  if (e instanceof ErroApi) {
    if (e.detalhes.length > 0) return e.detalhes.map((d) => `${d.campo}: ${d.mensagem}`).join(" · ");
    return e.message;
  }
  return "Ocorreu um erro inesperado.";
}
