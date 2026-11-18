import { Link, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { disponibilidade, equipamentos, ordens } from "../api/servicos";
import type { Criticidade, StatusOS } from "../api/tipos";
import { useAuth } from "../auth/Autenticacao";
import { CampoSelecao } from "../componentes/Campos";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { SeloCriticidade, SeloStatus } from "../componentes/Selos";
import { dataHora, numeroOS } from "../utilitarios/formatar";
import { TODOS_STATUS } from "../utilitarios/regras";
import { useCarregar } from "../utilitarios/useCarregar";

const CRITICIDADES: Criticidade[] = ["Baixa", "Média", "Alta", "Crítica"];

export function Ordens() {
  const { pode, usuario } = useAuth();
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") ?? "") as StatusOS | "";
  const criticidade = (params.get("criticidade") ?? "") as Criticidade | "";
  const equipamento = params.get("equipamento") ?? "";
  const tecnico = params.get("tecnico") ?? "";
  const encerrada = (params.get("encerrada") ?? "") as "" | "true" | "false";
  const antigas = params.get("antigas") === "1";

  function definir(chave: string, valor: string) {
    const novo = new URLSearchParams(params);
    if (valor) novo.set(chave, valor);
    else novo.delete(chave);
    setParams(novo, { replace: true });
  }

  const lista = useCarregar(
    () =>
      ordens.listar({
        status,
        criticidade,
        equipamento_id: equipamento ? Number(equipamento) : "",
        tecnico_id: tecnico ? Number(tecnico) : "",
        encerrada,
        mais_antigas_primeiro: antigas,
      }),
    [status, criticidade, equipamento, tecnico, encerrada, antigas],
  );
  const eqs = useCarregar(() => equipamentos.listar());
  const tecnicos = useCarregar(() => (pode("ver_disponibilidade") ? disponibilidade.listar() : Promise.resolve([])));

  const { dados, carregando, erro, recarregar } = lista;
  const temFiltro = !!(status || criticidade || equipamento || tecnico || encerrada || antigas);

  return (
    <>
      <div className="pagina-cab">
        <div>
          <h1>Ordens de serviço</h1>
          <p className="pagina-cab__sub">{dados ? `${dados.total} encontrada(s)` : "Acompanhamento"}</p>
        </div>
        <div className="linha">
          {usuario?.papel === "Técnico" && (
            <button type="button" className="btn btn--sec" onClick={() => definir("tecnico", String(usuario.id))}>
              Minhas OS
            </button>
          )}
          {pode("abrir_os") && (
            <Link className="btn" to="/ordens/nova">
              <Plus aria-hidden="true" /> Abrir OS
            </Link>
          )}
        </div>
      </div>

      <div className="cartao">
        <div className="filtros">
          <CampoSelecao rotulo="Status" value={status} onChange={(e) => definir("status", e.target.value)}>
            <option value="">Todos</option>
            {TODOS_STATUS.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </CampoSelecao>
          <CampoSelecao rotulo="Criticidade" value={criticidade} onChange={(e) => definir("criticidade", e.target.value)}>
            <option value="">Todas</option>
            {CRITICIDADES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </CampoSelecao>
          <CampoSelecao rotulo="Equipamento" value={equipamento} onChange={(e) => definir("equipamento", e.target.value)}>
            <option value="">Todos</option>
            {eqs.dados?.itens.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nome} — {e.modelo}
              </option>
            ))}
          </CampoSelecao>
          {(tecnicos.dados?.length ?? 0) > 0 && (
            <CampoSelecao rotulo="Técnico" value={tecnico} onChange={(e) => definir("tecnico", e.target.value)}>
              <option value="">Todos</option>
              {tecnicos.dados?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
            </CampoSelecao>
          )}
          <CampoSelecao rotulo="Situação" value={encerrada} onChange={(e) => definir("encerrada", e.target.value)}>
            <option value="">Todas</option>
            <option value="false">Em aberto</option>
            <option value="true">Encerradas</option>
          </CampoSelecao>
          <CampoSelecao rotulo="Ordem" value={antigas ? "1" : ""} onChange={(e) => definir("antigas", e.target.value)}>
            <option value="">Mais recentes primeiro</option>
            <option value="1">Mais antigas primeiro</option>
          </CampoSelecao>
        </div>
        {temFiltro && (
          <button type="button" className="btn btn--sec btn--peq" onClick={() => setParams({}, { replace: true })}>
            Limpar filtros
          </button>
        )}
      </div>

      {carregando && !dados ? (
        <Carregando />
      ) : erro && !dados ? (
        <ErroCarga mensagem={erro} aoTentar={recarregar} />
      ) : !dados || dados.itens.length === 0 ? (
        <Vazio titulo="Nenhuma OS encontrada">{temFiltro ? "Nenhuma OS atende aos filtros." : "Ainda não há ordens de serviço."}</Vazio>
      ) : (
        <div className="tabela-wrap">
          <table className="tabela-resp">
            <thead>
              <tr>
                <th>OS</th>
                <th>Equipamento</th>
                <th>Falha</th>
                <th>Status</th>
                <th>Criticidade</th>
                <th>Técnico</th>
                <th>Abertura</th>
              </tr>
            </thead>
            <tbody>
              {dados.itens.map((o) => (
                <tr key={o.numero}>
                  <td data-rotulo="OS">
                    <Link to={`/ordens/${o.numero}`}>{numeroOS(o.numero)}</Link>
                  </td>
                  <td data-rotulo="Equipamento">{o.equipamento.nome}</td>
                  <td data-rotulo="Falha" className="truncar">
                    {o.falha}
                  </td>
                  <td data-rotulo="Status">
                    <SeloStatus status={o.status} />
                  </td>
                  <td data-rotulo="Criticidade">
                    <SeloCriticidade criticidade={o.criticidade} />
                  </td>
                  <td data-rotulo="Técnico">{o.tecnico?.nome ?? "—"}</td>
                  <td data-rotulo="Abertura">{dataHora(o.data_abertura)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
