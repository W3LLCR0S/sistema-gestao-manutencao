import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { mensagemDeErro } from "../api/cliente";
import { equipamentos, ordens } from "../api/servicos";
import type { Equipamento } from "../api/tipos";
import { useAuth } from "../auth/Autenticacao";
import { useAvisos } from "../componentes/Avisos";
import { CampoSelecao, CampoTexto } from "../componentes/Campos";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { FormModal } from "../componentes/FormModal";
import { Confirmar, Modal } from "../componentes/Modal";
import { SeloAtivo, SeloCriticidade, SeloStatus } from "../componentes/Selos";
import { dataHora, numeroOS } from "../utilitarios/formatar";
import { useCarregar } from "../utilitarios/useCarregar";

type Dialogo =
  | { tipo: "novo" }
  | { tipo: "editar"; item: Equipamento }
  | { tipo: "detalhe"; item: Equipamento }
  | { tipo: "excluir"; item: Equipamento }
  | null;

export function Equipamentos() {
  const { pode } = useAuth();
  const avisos = useAvisos();
  const { dados, carregando, erro, recarregar } = useCarregar(() => equipamentos.listar());
  const [busca, setBusca] = useState("");
  const [situacao, setSituacao] = useState<"" | "ativo" | "inativo">("");
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [ocupado, setOcupado] = useState(false);
  const gerir = pode("gerir_equipamentos");

  const itens = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return (dados?.itens ?? []).filter(
      (e) =>
        (!termo || `${e.nome} ${e.modelo}`.toLowerCase().includes(termo)) &&
        (situacao === "" || (situacao === "ativo") === e.ativo),
    );
  }, [dados, busca, situacao]);

  async function alternar(e: Equipamento) {
    try {
      if (e.ativo) await equipamentos.inativar(e.id);
      else await equipamentos.reativar(e.id);
      avisos.ok(e.ativo ? "Equipamento inativado." : "Equipamento reativado.");
      recarregar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
    }
  }

  async function excluir(e: Equipamento) {
    setOcupado(true);
    try {
      await equipamentos.excluir(e.id);
      avisos.ok("Equipamento excluído.");
      setDialogo(null);
      recarregar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
      setDialogo(null);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <div className="pagina-cab">
        <div>
          <h1>Equipamentos</h1>
          <p className="pagina-cab__sub">{dados ? `${dados.total} cadastrado(s)` : "Cadastro e situação"}</p>
        </div>
        {gerir && (
          <button type="button" className="btn" onClick={() => setDialogo({ tipo: "novo" })}>
            <Plus aria-hidden="true" /> Novo equipamento
          </button>
        )}
      </div>

      <div className="cartao">
        <div className="filtros">
          <CampoTexto rotulo="Buscar por nome ou modelo" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
          <CampoSelecao rotulo="Situação" value={situacao} onChange={(e) => setSituacao(e.target.value as typeof situacao)}>
            <option value="">Todos</option>
            <option value="ativo">Ativos</option>
            <option value="inativo">Inativos</option>
          </CampoSelecao>
        </div>
      </div>

      {carregando && !dados ? (
        <Carregando />
      ) : erro && !dados ? (
        <ErroCarga mensagem={erro} aoTentar={recarregar} />
      ) : itens.length === 0 ? (
        <Vazio titulo="Nenhum equipamento encontrado">
          {dados?.total ? "Ajuste a busca ou os filtros." : "Cadastre o primeiro equipamento."}
        </Vazio>
      ) : (
        <div className="tabela-wrap">
          <table className="tabela-resp">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Modelo</th>
                <th>Situação</th>
                <th>Atendimento</th>
                <th>
                  <span className="sr-only">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {itens.map((e) => (
                <tr key={e.id}>
                  <td data-rotulo="Nome">
                    <button type="button" className="btn-link" onClick={() => setDialogo({ tipo: "detalhe", item: e })}>
                      {e.nome}
                    </button>
                  </td>
                  <td data-rotulo="Modelo">{e.modelo}</td>
                  <td data-rotulo="Situação">
                    <SeloAtivo ativo={e.ativo} />
                  </td>
                  <td data-rotulo="Atendimento">{e.situacao}</td>
                  <td className="celula-acoes">
                    <button type="button" className="btn btn--sec btn--peq" onClick={() => setDialogo({ tipo: "detalhe", item: e })}>
                      Detalhes
                    </button>{" "}
                    {gerir && (
                      <>
                        <button type="button" className="btn btn--sec btn--peq" onClick={() => setDialogo({ tipo: "editar", item: e })}>
                          Editar
                        </button>{" "}
                        <button type="button" className="btn btn--sec btn--peq" onClick={() => alternar(e)}>
                          {e.ativo ? "Inativar" : "Reativar"}
                        </button>{" "}
                        <button type="button" className="btn btn--sec btn--peq" onClick={() => setDialogo({ tipo: "excluir", item: e })}>
                          Excluir
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialogo?.tipo === "novo" && (
        <FormularioEquipamento
          aoFechar={() => setDialogo(null)}
          aoSalvar={async (d) => {
            await equipamentos.criar(d);
            avisos.ok("Equipamento cadastrado.");
            recarregar();
          }}
        />
      )}
      {dialogo?.tipo === "editar" && (
        <FormularioEquipamento
          inicial={dialogo.item}
          aoFechar={() => setDialogo(null)}
          aoSalvar={async (d) => {
            await equipamentos.atualizar(dialogo.item.id, d);
            avisos.ok("Equipamento atualizado.");
            recarregar();
          }}
        />
      )}
      {dialogo?.tipo === "excluir" && (
        <Confirmar
          titulo="Excluir equipamento"
          mensagem={
            <p>
              Excluir <strong>{dialogo.item.nome}</strong>? Só é possível se não houver OS vinculadas; caso contrário, inative-o.
            </p>
          }
          rotuloConfirmar="Excluir"
          perigo
          ocupado={ocupado}
          aoConfirmar={() => excluir(dialogo.item)}
          aoFechar={() => setDialogo(null)}
        />
      )}
      {dialogo?.tipo === "detalhe" && <DetalheEquipamento item={dialogo.item} aoFechar={() => setDialogo(null)} />}
    </>
  );
}

function FormularioEquipamento({
  inicial,
  aoFechar,
  aoSalvar,
}: {
  inicial?: Equipamento;
  aoFechar: () => void;
  aoSalvar: (d: { nome: string; modelo: string }) => Promise<void>;
}) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [modelo, setModelo] = useState(inicial?.modelo ?? "");
  return (
    <FormModal
      titulo={inicial ? "Editar equipamento" : "Novo equipamento"}
      rotuloEnviar="Salvar"
      aoFechar={aoFechar}
      aoEnviar={() => aoSalvar({ nome: nome.trim(), modelo: modelo.trim() })}
      validar={() => (!nome.trim() || !modelo.trim() ? "Informe o nome e o modelo." : null)}
    >
      <CampoTexto rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={200} required />
      <CampoTexto rotulo="Modelo" value={modelo} onChange={(e) => setModelo(e.target.value)} maxLength={200} required />
    </FormModal>
  );
}

function DetalheEquipamento({ item, aoFechar }: { item: Equipamento; aoFechar: () => void }) {
  const { pode } = useAuth();
  const podeVerOS = pode("ver_os");
  const { dados, carregando, erro } = useCarregar(
    () => (podeVerOS ? ordens.listar({ equipamento_id: item.id, limite: 50 }) : Promise.resolve(null)),
    [item.id],
  );
  return (
    <Modal titulo={item.nome} aoFechar={aoFechar} largo>
      <dl className="detalhes">
        <div>
          <dt>Modelo</dt>
          <dd>{item.modelo}</dd>
        </div>
        <div>
          <dt>Situação</dt>
          <dd>
            <SeloAtivo ativo={item.ativo} /> · {item.situacao}
          </dd>
        </div>
      </dl>
      <h3 style={{ marginTop: "1.25rem" }}>Histórico de OS</h3>
      {!podeVerOS ? (
        <p>Seu cargo não permite consultar OS.</p>
      ) : carregando ? (
        <Carregando />
      ) : erro ? (
        <p role="alert">{erro}</p>
      ) : !dados || dados.itens.length === 0 ? (
        <p>Nenhuma OS registrada para este equipamento.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {dados.itens.map((o) => (
            <li key={o.numero} className="linha" style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--cinza-200)" }}>
              <Link to={`/ordens/${o.numero}`} onClick={aoFechar}>
                {numeroOS(o.numero)}
              </Link>
              <SeloStatus status={o.status} />
              <SeloCriticidade criticidade={o.criticidade} />
              <small>{dataHora(o.data_abertura)}</small>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
