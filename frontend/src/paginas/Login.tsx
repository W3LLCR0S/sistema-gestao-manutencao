import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Wrench } from "lucide-react";
import { ErroApi, mensagemDeErro } from "../api/cliente";
import { useAuth } from "../auth/Autenticacao";
import { CampoTexto } from "../componentes/Campos";
import { Alerta } from "../componentes/Estados";
import { matriculaValida, normalizarDigitacaoDaMatricula, TAMANHO_DA_MATRICULA } from "../utilitarios/matricula";

export function Login() {
  const { usuario, verificando, entrar, aviso } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const [matricula, setMatricula] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const destino = (local.state as { de?: string } | null)?.de ?? "/";

  if (!verificando && usuario) return <Navigate to={destino} replace />;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!matricula || !senha) {
      setErro("Informe a matrícula e a senha.");
      return;
    }
    if (!matriculaValida(matricula)) {
      setErro("A matrícula tem duas letras e seis números, como KM482731.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await entrar(matricula, senha);
      navegar(destino, { replace: true });
    } catch (ex) {
      setSenha("");
      setErro(
        ex instanceof ErroApi && ex.status === 401
          ? "Matrícula ou senha incorretos."
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
            rotulo="Matrícula"
            value={matricula}
            onChange={(e) => setMatricula(normalizarDigitacaoDaMatricula(e.target.value))}
            autoComplete="username"
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            maxLength={TAMANHO_DA_MATRICULA}
            placeholder="AA999999"
            ajuda="Duas letras e seis números. Ex.: KM482731"
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
