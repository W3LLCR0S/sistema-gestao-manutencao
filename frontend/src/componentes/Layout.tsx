import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  ClipboardList,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  ShieldCheck,
  Users,
  Wrench,
  X,
} from "lucide-react";
import { useAuth } from "../auth/Autenticacao";
import type { Permissao } from "../api/tipos";

interface Item {
  para: string;
  rotulo: string;
  icone: typeof Wrench;
  permissao?: Permissao;
}
const ITENS: Item[] = [
  { para: "/", rotulo: "Painel", icone: LayoutDashboard, permissao: "ver_os" },
  { para: "/ordens", rotulo: "Ordens de serviço", icone: ClipboardList, permissao: "ver_os" },
  { para: "/equipamentos", rotulo: "Equipamentos", icone: Wrench, permissao: "ver_equipamentos" },
  { para: "/usuarios", rotulo: "Usuários", icone: Users, permissao: "gerir_usuarios" },
  { para: "/cargos", rotulo: "Cargos e permissões", icone: ShieldCheck, permissao: "gerir_usuarios" },
];

export function Layout() {
  const { usuario, sair, pode } = useAuth();
  const [aberto, setAberto] = useState(false);
  const local = useLocation();
  const navegar = useNavigate();

  // fecha o menu móvel ao navegar
  useEffect(() => setAberto(false), [local.pathname]);
  useEffect(() => {
    if (!aberto) return;
    const t = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("keydown", t);
    return () => document.removeEventListener("keydown", t);
  }, [aberto]);

  const itens = ITENS.filter((i) => !i.permissao || pode(i.permissao));

  async function aoSair() {
    await sair();
    navegar("/login", { replace: true });
  }

  return (
    <div className="app">
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="topo">
        <button
          type="button"
          className="btn-icone topo__menu"
          aria-label={aberto ? "Fechar menu" : "Abrir menu"}
          aria-expanded={aberto}
          aria-controls="navegacao"
          onClick={() => setAberto((v) => !v)}
        >
          {aberto ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <span className="marca marca--topo">
          <Wrench aria-hidden="true" /> Manutenção
        </span>
        <span className="topo__usuario">{usuario?.nome}</span>
      </header>

      {aberto && <div className="cortina" onClick={() => setAberto(false)} aria-hidden="true" />}
      <aside className={aberto ? "lateral lateral--aberta" : "lateral"}>
        <div className="marca">
          <Wrench aria-hidden="true" />
          <div>
            <strong>Gestão de Manutenção</strong>
            <small>Equipamentos e OS</small>
          </div>
        </div>
        <nav id="navegacao" aria-label="Principal">
          {itens.map(({ para, rotulo, icone: Icone }) => (
            <NavLink key={para} to={para} end={para === "/"} className="nav__item">
              <Icone aria-hidden="true" />
              <span>{rotulo}</span>
            </NavLink>
          ))}
        </nav>
        <div className="lateral__rodape">
          <div className="perfil">
            <span className="perfil__nome">{usuario?.nome}</span>
            <span className="perfil__papel">
              {usuario?.papel} · {usuario?.cargo.nome}
            </span>
          </div>
          <NavLink to="/senha" className="nav__item">
            <KeyRound aria-hidden="true" />
            <span>Alterar senha</span>
          </NavLink>
          <button type="button" className="nav__item nav__item--botao" onClick={aoSair}>
            <LogOut aria-hidden="true" />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      <main id="conteudo" className="principal" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
