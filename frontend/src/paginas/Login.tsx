import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Wrench } from "lucide-react";
import { ErroApi, mensagemDeErro } from "../api/cliente";
import { useAuth } from "../auth/Autenticacao";
import { CampoTexto } from "../componentes/Campos";
import { Alerta } from "../componentes/Estados";

export function Login() {
  const { usuario, verificando, entrar, aviso } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const destino = (local.state as { de?: string } | null)?.de ?? "/";

  if (!verificando && usuario) return <Navigate to={destino} replace />;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!login.trim() || !senha) {
      setErro("Informe o usuário e a senha.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await entrar(login.trim(), senha);
      navegar(destino, { replace: true });
    } catch (ex) {
      setSenha("");
      setErro(
        ex instanceof ErroApi && ex.status === 401
          ? "Usuário ou senha incorretos."
          : mensagemDeErro(ex),
      );
      setEnviando(false);
    }
  }

  return (
    <main className="login">
      <div className="login__cartao">
        <div className="login__marca">
          <Wrench aria-hidden="true" size={30} />
          <h1>Gestão de Manutenção</h1>
        </div>
        <form onSubmit={enviar} noValidate>
          {aviso && <Alerta tipo="info">{aviso}</Alerta>}
          {erro && <Alerta>{erro}</Alerta>}
          <CampoTexto
            rotulo="Usuário"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            autoFocus
            required
          />
          <CampoTexto
            rotulo="Senha"
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button type="submit" className="btn" style={{ width: "100%" }} disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}
