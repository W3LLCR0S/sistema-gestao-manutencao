import { useState, type FormEvent } from "react";
import { mensagemDeErro } from "../api/cliente";
import { autenticacao, usuarios } from "../api/servicos";
import type { Disponibilidade } from "../api/tipos";
import { useAuth } from "../auth/Autenticacao";
import { useAvisos } from "../componentes/Avisos";
import { CampoSelecao, CampoTexto } from "../componentes/Campos";
import { Alerta } from "../componentes/Estados";
import { SeloDisponibilidade } from "../componentes/Selos";

export function AlterarSenha() {
  const { usuario, atualizarUsuario } = useAuth();
  const avisos = useAvisos();
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirma, setConfirma] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!atual || !nova) return setErro("Preencha a senha atual e a nova senha.");
    if (nova !== confirma) return setErro("A confirmação não confere com a nova senha.");
    setEnviando(true);
    setErro(null);
    try {
      await autenticacao.alterarSenha(atual, nova);
      setAtual("");
      setNova("");
      setConfirma("");
      avisos.ok("Senha alterada. Suas outras sessões foram encerradas.");
    } catch (ex) {
      setErro(mensagemDeErro(ex));
    } finally {
      setEnviando(false);
    }
  }

  async function mudarDisponibilidade(valor: Disponibilidade) {
    try {
      const u = await usuarios.minhaDisponibilidade(valor);
      if (usuario) atualizarUsuario({ ...usuario, ...u });
      avisos.ok("Disponibilidade atualizada.");
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
    }
  }

  return (
    <>
      <div className="pagina-cab">
        <h1>Minha conta</h1>
      </div>
      <div className="grade grade--2">
        <section className="cartao" aria-labelledby="t-dados">
          <h2 id="t-dados">Meus dados</h2>
          <dl className="detalhes">
            <div>
              <dt>Nome</dt>
              <dd>{usuario?.nome}</dd>
            </div>
            <div>
              <dt>Matrícula</dt>
              <dd>{usuario?.matricula ?? "—"}</dd>
            </div>
            <div>
              <dt>Papel</dt>
              <dd>{usuario?.papel}</dd>
            </div>
            <div>
              <dt>Cargo</dt>
              <dd>{usuario?.cargo.nome}</dd>
            </div>
            <div>
              <dt>Disponibilidade</dt>
              <dd>{usuario && <SeloDisponibilidade valor={usuario.disponibilidade} />}</dd>
            </div>
          </dl>
          {usuario?.papel === "Técnico" && (
            <div style={{ marginTop: "1rem" }}>
              <CampoSelecao
                rotulo="Minha disponibilidade"
                ajuda="“Em atendimento” é automático quando há OS em execução."
                value={usuario.disponibilidade === "Ausente" ? "Ausente" : "Disponível"}
                onChange={(e) => mudarDisponibilidade(e.target.value as Disponibilidade)}
              >
                <option value="Disponível">Disponível</option>
                <option value="Ausente">Ausente</option>
              </CampoSelecao>
            </div>
          )}
        </section>
        <section className="cartao" aria-labelledby="t-senha">
          <h2 id="t-senha">Alterar senha</h2>
          <form onSubmit={enviar} noValidate>
            {erro && <Alerta>{erro}</Alerta>}
            <CampoTexto rotulo="Senha atual" type="password" value={atual} onChange={(e) => setAtual(e.target.value)} autoComplete="current-password" />
            <CampoTexto rotulo="Nova senha" type="password" value={nova} onChange={(e) => setNova(e.target.value)} autoComplete="new-password" />
            <CampoTexto rotulo="Confirmar nova senha" type="password" value={confirma} onChange={(e) => setConfirma(e.target.value)} autoComplete="new-password" />
            <button type="submit" className="btn" disabled={enviando}>
              {enviando ? "Salvando…" : "Alterar senha"}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
