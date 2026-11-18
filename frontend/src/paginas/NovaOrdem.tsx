import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { mensagemDeErro } from "../api/cliente";
import { equipamentos, ordens } from "../api/servicos";
import type { Criticidade } from "../api/tipos";
import { useAvisos } from "../componentes/Avisos";
import { CampoAreaTexto, CampoSelecao } from "../componentes/Campos";
import { Alerta, Carregando, ErroCarga } from "../componentes/Estados";
import { useCarregar } from "../utilitarios/useCarregar";

export function NovaOrdem() {
  const navegar = useNavigate();
  const avisos = useAvisos();
  const { dados, carregando, erro, recarregar } = useCarregar(() => equipamentos.listar(true));
  const [equipamentoId, setEquipamentoId] = useState("");
  const [criticidade, setCriticidade] = useState<Criticidade>("Média");
  const [falha, setFalha] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!equipamentoId) return setMsg("Escolha o equipamento.");
    if (!falha.trim()) return setMsg("Descreva a falha.");
    setEnviando(true);
    setMsg(null);
    try {
      const o = await ordens.abrir({ equipamento_id: Number(equipamentoId), falha: falha.trim(), criticidade });
      avisos.ok(`OS #${String(o.numero).padStart(4, "0")} aberta.`);
      navegar(`/ordens/${o.numero}`);
    } catch (ex) {
      setMsg(mensagemDeErro(ex));
      setEnviando(false);
    }
  }

  if (carregando && !dados) return <Carregando />;
  if (erro && !dados) return <ErroCarga mensagem={erro} aoTentar={recarregar} />;

  return (
    <>
      <div className="pagina-cab">
        <h1>Abrir ordem de serviço</h1>
      </div>
      <form className="cartao" onSubmit={enviar} noValidate>
        {msg && <Alerta>{msg}</Alerta>}
        {dados && dados.itens.length === 0 ? (
          <Alerta tipo="info">
            Não há equipamentos ativos. Cadastre um em <Link to="/equipamentos">Equipamentos</Link>.
          </Alerta>
        ) : (
          <>
            <div className="form-grade">
              <CampoSelecao rotulo="Equipamento" value={equipamentoId} onChange={(e) => setEquipamentoId(e.target.value)} required>
                <option value="">Selecione…</option>
                {dados?.itens.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome} — {e.modelo}
                  </option>
                ))}
              </CampoSelecao>
              <CampoSelecao rotulo="Criticidade" value={criticidade} onChange={(e) => setCriticidade(e.target.value as Criticidade)}>
                <option>Baixa</option>
                <option>Média</option>
                <option>Alta</option>
                <option>Crítica</option>
              </CampoSelecao>
              <div className="largo">
                <CampoAreaTexto rotulo="Descrição da falha" value={falha} onChange={(e) => setFalha(e.target.value)} maxLength={4000} required />
              </div>
            </div>
            <div className="acoes">
              <Link className="btn btn--sec" to="/ordens">
                Cancelar
              </Link>
              <button type="submit" className="btn" disabled={enviando}>
                {enviando ? "Abrindo…" : "Abrir OS"}
              </button>
            </div>
          </>
        )}
      </form>
    </>
  );
}
