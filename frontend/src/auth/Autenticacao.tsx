import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { aoSessaoExpirar, definirCsrf } from "../api/cliente";
import { autenticacao } from "../api/servicos";
import type { Permissao, Sessao, UsuarioAtual } from "../api/tipos";
import { Carregando } from "../componentes/Estados";
import { tem } from "../utilitarios/regras";

interface Contexto {
  usuario: UsuarioAtual | null;
  verificando: boolean;
  aviso: string | null;
  entrar: (matricula: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
  atualizarUsuario: (u: UsuarioAtual) => void;
  recarregarUsuario: () => Promise<void>;
  pode: (p: Permissao) => boolean;
}

const Ctx = createContext<Contexto | null>(null);

export function ProvedorAutenticacao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioAtual | null>(null);
  const [verificando, setVerificando] = useState(true);
  const [aviso, setAviso] = useState<string | null>(null);

  const aplicar = useCallback((s: Sessao) => {
    definirCsrf(s.csrf_token);
    setUsuario(s.usuario);
    setAviso(null);
  }, []);

  useEffect(() => {
    // 401 em qualquer chamada: a sessão expirou ou foi revogada → volta ao login.
    aoSessaoExpirar(() => {
      definirCsrf(null);
      setUsuario((atual) => {
        if (atual) setAviso("Sua sessão expirou. Entre novamente.");
        return null;
      });
    });
    let ativo = true;
    autenticacao
      .eu()
      .then((s) => ativo && aplicar(s))
      .catch(() => undefined)
      .finally(() => ativo && setVerificando(false));
    return () => {
      ativo = false;
      aoSessaoExpirar(null);
    };
  }, [aplicar]);

  const entrar = useCallback(
    async (matricula: string, senha: string) => {
      aplicar(await autenticacao.login(matricula, senha));
    },
    [aplicar],
  );

  const sair = useCallback(async () => {
    try {
      await autenticacao.logout();
    } catch {
      // mesmo se a rede falhar, a interface sai; o servidor expira a sessão sozinho
    }
    definirCsrf(null);
    setUsuario(null);
    setAviso(null);
  }, []);

  const recarregarUsuario = useCallback(async () => {
    aplicar(await autenticacao.eu());
  }, [aplicar]);

  const valor = useMemo<Contexto>(
    () => ({
      usuario,
      verificando,
      aviso,
      entrar,
      sair,
      atualizarUsuario: setUsuario,
      recarregarUsuario,
      pode: (p) => tem(usuario, p),
    }),
    [usuario, verificando, aviso, entrar, sair, recarregarUsuario],
  );
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useAuth(): Contexto {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth fora do ProvedorAutenticacao");
  return c;
}

/** Protege rotas: sem sessão → /login (guardando o destino); sem permissão → aviso. */
export function RotaProtegida({ children, permissao }: { children: ReactNode; permissao?: Permissao }) {
  const { usuario, verificando, pode } = useAuth();
  const local = useLocation();
  if (verificando) return <Carregando texto="Verificando sessão…" tela />;
  if (!usuario) return <Navigate to="/login" replace state={{ de: local.pathname + local.search }} />;
  if (permissao && !pode(permissao)) {
    return (
      <div className="vazio" role="alert">
        <h2>Acesso negado</h2>
        <p>Seu cargo não tem permissão para esta área.</p>
      </div>
    );
  }
  return <>{children}</>;
}
