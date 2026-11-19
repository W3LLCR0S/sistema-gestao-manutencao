import { Link } from "react-router-dom";
import { painel } from "../api/servicos";
import { useAuth } from "../auth/Autenticacao";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { SeloCriticidade, SeloDisponibilidade, SeloStatus } from "../componentes/Selos";
import { dataHora, numeroOS } from "../utilitarios/formatar";
import { TODOS_STATUS } from "../utilitarios/regras";
import { useCarregar } from "../utilitarios/useCarregar";

export function Painel() {
  const { usuario, pode } = useAuth();
  const { dados, carregando, erro, recarregar } = useCarregar(() => painel.obter());

  if (carregando && !dados) return <Carregando />;
  if (erro && !dados) return <ErroCarga mensagem={erro} aoTentar={recarregar} />;
  if (!dados) return null;

  const porStatus = new Map(dados.por_status.map((s) => [s.status, s.quantidade]));
  const maior = Math.max(1, ...TODOS_STATUS.map((s) => porStatus.get(s) ?? 0));
  const pendentes = (porStatus.get("Aberta") ?? 0) + (porStatus.get("Atribuída") ?? 0);
  const emExecucao = (porStatus.get("Em Execução") ?? 0) + (porStatus.get("Aguardando Peça") ?? 0);

  return (
    <>
      <div className="pagina-cab">
        <div>
          <h1>Painel</h1>
          <p className="pagina-cab__sub">Olá, {usuario?.nome}. Resumo das ordens de serviço.</p>
        </div>
        <div className="linha">
          <button type="button" className="btn btn--sec" onClick={recarregar}>
            Atualizar
          </button>
          {pode("abrir_os") && (
            <Link className="btn" to="/ordens/nova">
              Abrir OS
            </Link>
          )}
        </div>
      </div>

      <div className="grade grade--4" style={{ marginBottom: "1rem" }}>
        <div className="indicador">
          <div className="indicador__valor">{dados.total}</div>
          <div className="indicador__rotulo">OS no total</div>
        </div>
        <div className="indicador indicador--alerta">
          <div className="indicador__valor">{pendentes}</div>
          <div className="indicador__rotulo">Pendentes (abertas/atribuídas)</div>
        </div>
        <div className="indicador indicador--roxo">
          <div className="indicador__valor">{emExecucao}</div>
          <div className="indicador__rotulo">Em execução</div>
        </div>
        <div className="indicador indicador--ok">
          <div className="indicador__valor">{dados.minhas_em_aberto}</div>
          <div className="indicador__rotulo">Minhas OS em aberto</div>
        </div>
      </div>

      <div className="grade grade--2">
        <section className="cartao" aria-labelledby="t-status">
          <h2 id="t-status">Ordens por status</h2>
          {TODOS_STATUS.map((s) => {
            const q = porStatus.get(s) ?? 0;
            return (
              <div className="linha-barra" key={s}>
                <Link to={`/ordens?status=${encodeURIComponent(s)}`}>{s}</Link>
                <div className="barra" aria-hidden="true">
                  <span style={{ width: `${(q / maior) * 100}%` }} />
                </div>
                <b>{q}</b>
              </div>
            );
          })}
        </section>

        <section className="cartao" aria-labelledby="t-crit">
          <h2 id="t-crit">Em aberto por criticidade</h2>
          {dados.por_criticidade_em_aberto.length === 0 ? (
            <Vazio titulo="Nenhuma OS em aberto" />
          ) : (
            <ul className="lista-simples" style={{ listStyle: "none", padding: 0 }}>
              {dados.por_criticidade_em_aberto.map((c) => (
                <li key={c.criticidade} className="linha" style={{ justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <SeloCriticidade criticidade={c.criticidade} />
                  <b>{c.quantidade}</b>
                </li>
              ))}
            </ul>
          )}
          {dados.tecnicos && (
            <>
              <h3 style={{ marginTop: "1rem" }}>Técnicos</h3>
              {dados.tecnicos.length === 0 ? (
                <p>Nenhum técnico cadastrado.</p>
              ) : (
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {dados.tecnicos.map((t) => (
                    <li key={t.id} className="linha" style={{ justifyContent: "space-between", marginBottom: "0.4rem" }}>
                      <span>
                        {t.nome} <small>({t.carga} OS)</small>
                      </span>
                      <SeloDisponibilidade valor={t.disponibilidade} />
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      </div>

      <section className="cartao" aria-labelledby="t-rec">
        <h2 id="t-rec">Atividade recente</h2>
        {dados.recentes.length === 0 ? (
          <Vazio titulo="Nenhuma ordem de serviço ainda">Abra a primeira OS para começar.</Vazio>
        ) : (
          <div className="tabela-wrap">
            <table className="tabela-resp">
              <thead>
                <tr>
                  <th>OS</th>
                  <th>Equipamento</th>
                  <th>Status</th>
                  <th>Criticidade</th>
                  <th>Técnico</th>
                  <th>Abertura</th>
                </tr>
              </thead>
              <tbody>
                {dados.recentes.map((o) => (
                  <tr key={o.numero}>
                    <td data-rotulo="OS">
                      <Link to={`/ordens/${o.numero}`}>{numeroOS(o.numero)}</Link>
                    </td>
                    <td data-rotulo="Equipamento">{o.equipamento.nome}</td>
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
      </section>
    </>
  );
}
