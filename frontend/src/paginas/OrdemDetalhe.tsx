import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { mensagemDeErro } from "../api/cliente";
import { disponibilidade, ordens } from "../api/servicos";
import type { Ordem, Peca, StatusOS } from "../api/tipos";
import { useAuth } from "../auth/Autenticacao";
import { useAvisos } from "../componentes/Avisos";
import { CampoAreaTexto, CampoSelecao, CampoTexto } from "../componentes/Campos";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { FormModal } from "../componentes/FormModal";
import { Confirmar } from "../componentes/Modal";
import { SeloCriticidade, SeloStatus } from "../componentes/Selos";
import { dataHora, horas, lerNumero, numeroOS } from "../utilitarios/formatar";
import { acoesDisponiveis } from "../utilitarios/regras";
import { useCarregar } from "../utilitarios/useCarregar";

type Dialogo =
  | "diagnostico"
  | "reparo"
  | "status"
  | "concluir"
  | "atribuir"
  | "aprovar"
  | "reprovar"
  | "cancelar"
  | "apontamento"
  | null;

export function OrdemDetalhe() {
  const numero = Number(useParams().numero);
  const { usuario } = useAuth();
  const avisos = useAvisos();
  const valido = Number.isInteger(numero) && numero > 0;
  const os = useCarregar(() => ordens.obter(numero), [numero]);
  const hist = useCarregar(() => ordens.historico(numero), [numero]);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [ocupado, setOcupado] = useState(false);

  if (!valido)
    return (
      <Vazio titulo="Número de OS inválido">
        <Link to="/ordens">Voltar às ordens</Link>
      </Vazio>
    );
  if (os.carregando && !os.dados) return <Carregando />;
  if (os.erro && !os.dados)
    return (
      <>
        <ErroCarga mensagem={os.erro} aoTentar={os.recarregar} />
        <Link to="/ordens">Voltar às ordens</Link>
      </>
    );
  const o = os.dados;
  if (!o) return null;

  const acoes = acoesDisponiveis(o, usuario);
  const atualizar = () => {
    os.recarregar();
    hist.recarregar();
  };
  const fechar = () => setDialogo(null);

  async function simples(acao: () => Promise<unknown>, ok: string) {
    setOcupado(true);
    try {
      await acao();
      avisos.ok(ok);
      fechar();
      atualizar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
      fechar();
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <Link to="/ordens" className="linha" style={{ marginBottom: "0.75rem" }}>
        <ArrowLeft aria-hidden="true" size={18} /> Ordens de serviço
      </Link>
      <div className="pagina-cab">
        <div>
          <h1>{numeroOS(o.numero)}</h1>
          <p className="pagina-cab__sub">
            {o.equipamento.nome} — {o.equipamento.modelo}
          </p>
        </div>
        <div className="linha">
          <SeloStatus status={o.status} />
          <SeloCriticidade criticidade={o.criticidade} />
        </div>
      </div>

      <section className="cartao" aria-labelledby="t-res">
        <h2 id="t-res">Resumo</h2>
        <dl className="detalhes">
          <div className="largo">
            <dt>Falha relatada</dt>
            <dd>{o.falha}</dd>
          </div>
          <div>
            <dt>Aberta por</dt>
            <dd>{o.aberta_por.nome}</dd>
          </div>
          <div>
            <dt>Técnico responsável</dt>
            <dd>{o.tecnico?.nome ?? "Sem técnico"}</dd>
          </div>
          <div>
            <dt>Abertura</dt>
            <dd>{dataHora(o.data_abertura)}</dd>
          </div>
          <div>
            <dt>Conclusão</dt>
            <dd>{dataHora(o.data_conclusao)}</dd>
          </div>
          {o.status === "Cancelada" && (
            <div className="largo">
              <dt>Motivo do cancelamento</dt>
              <dd>{o.motivo_cancelamento || "—"}</dd>
            </div>
          )}
        </dl>
      </section>

      {(acoes.atribuir ||
        acoes.diagnosticar ||
        acoes.reparo ||
        acoes.statusPossiveis.length > 0 ||
        acoes.concluir ||
        acoes.aprovar ||
        acoes.cancelar ||
        acoes.apontamento) && (
        <section className="cartao" aria-labelledby="t-acoes">
          <h2 id="t-acoes">Ações</h2>
          <div className="acoes acoes--inicio" style={{ marginTop: 0 }}>
            {acoes.atribuir && (
              <button type="button" className="btn" onClick={() => setDialogo("atribuir")}>
                {o.tecnico ? "Reatribuir técnico" : "Atribuir técnico"}
              </button>
            )}
            {acoes.diagnosticar && (
              <button type="button" className="btn" onClick={() => setDialogo("diagnostico")}>
                Registrar diagnóstico
              </button>
            )}
            {acoes.reparo && (
              <button type="button" className="btn" onClick={() => setDialogo("reparo")}>
                Apontar reparo
              </button>
            )}
            {acoes.statusPossiveis.length > 0 && (
              <button type="button" className="btn btn--sec" onClick={() => setDialogo("status")}>
                Alterar status
              </button>
            )}
            {acoes.concluir && (
              <button type="button" className="btn" onClick={() => setDialogo("concluir")}>
                Concluir tecnicamente
              </button>
            )}
            {acoes.aprovar && (
              <>
                <button type="button" className="btn" onClick={() => setDialogo("aprovar")}>
                  Aprovar e encerrar
                </button>
                <button type="button" className="btn btn--sec" onClick={() => setDialogo("reprovar")}>
                  Reprovar
                </button>
              </>
            )}
            {acoes.apontamento && (
              <button type="button" className="btn btn--sec" onClick={() => setDialogo("apontamento")}>
                Adicionar observação
              </button>
            )}
            {acoes.cancelar && (
              <button type="button" className="btn btn--perigo" onClick={() => setDialogo("cancelar")}>
                Cancelar OS
              </button>
            )}
          </div>
        </section>
      )}

      <div className="grade grade--2">
        <section className="cartao" aria-labelledby="t-diag">
          <h2 id="t-diag">Diagnóstico</h2>
          {o.diagnostico ? (
            <dl className="detalhes" style={{ gridTemplateColumns: "1fr" }}>
              <div>
                <dt>Parecer</dt>
                <dd>{o.diagnostico}</dd>
              </div>
              <div>
                <dt>Causa raiz</dt>
                <dd>{o.causa_raiz || "—"}</dd>
              </div>
              {o.teste_funcional && (
                <div>
                  <dt>Teste funcional</dt>
                  <dd>{o.teste_funcional}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p>Ainda não há diagnóstico.</p>
          )}
        </section>

        <section className="cartao" aria-labelledby="t-exec">
          <h2 id="t-exec">Execução</h2>
          <p>
            <strong>Horas trabalhadas:</strong> {horas(o.horas_trabalhadas)}
          </p>
          <h3>Intervenções</h3>
          {o.intervencoes.length ? (
            <ul className="lista-simples">
              {o.intervencoes.map((i, n) => (
                <li key={n}>{i}</li>
              ))}
            </ul>
          ) : (
            <p>Nenhuma intervenção registrada.</p>
          )}
          <h3 style={{ marginTop: "1rem" }}>Peças e materiais</h3>
          {o.pecas.length ? (
            <ul className="lista-simples">
              {o.pecas.map((p, n) => (
                <li key={n}>
                  {p.descricao} — {p.quantidade.toLocaleString("pt-BR")}
                </li>
              ))}
            </ul>
          ) : (
            <p>Nenhuma peça utilizada.</p>
          )}
        </section>
      </div>

      <section className="cartao" aria-labelledby="t-hist">
        <h2 id="t-hist">Histórico</h2>
        {hist.carregando && !hist.dados ? (
          <Carregando />
        ) : hist.erro && !hist.dados ? (
          <ErroCarga mensagem={hist.erro} aoTentar={hist.recarregar} />
        ) : (
          <ol className="linha-tempo">
            {hist.dados?.map((s) => (
              <li key={s.numero}>
                <strong>{s.tipo}</strong>
                {s.responsavel && <> · {s.responsavel.nome}</>}
                <br />
                <small>{dataHora(s.data)}</small>
                {s.descricao && <p style={{ margin: "0.25rem 0 0" }}>{s.descricao}</p>}
                {(s.horas > 0 || s.pecas.length > 0) && (
                  <small>
                    {s.horas > 0 && <>{horas(s.horas)} </>}
                    {s.pecas.length > 0 && <>· Peças: {s.pecas.map((p) => `${p.descricao} (${p.quantidade})`).join(", ")}</>}
                  </small>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      {dialogo === "diagnostico" && <FormDiagnostico os={o} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "reparo" && <FormReparo os={o} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "status" && <FormStatus os={o} opcoes={acoes.statusPossiveis} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "concluir" && <FormConcluir os={o} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "atribuir" && <FormAtribuir os={o} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "apontamento" && <FormApontamento os={o} aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "reprovar" && <FormMotivo titulo="Reprovar OS" rotulo="Motivo da reprovação" enviar="Reprovar" os={o} acao={(m) => ordens.reprovar(o.numero, m)} ok="OS reprovada; voltou para execução." aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "cancelar" && <FormMotivo titulo="Cancelar OS" rotulo="Motivo do cancelamento" enviar="Cancelar OS" perigo os={o} acao={(m) => ordens.cancelar(o.numero, m)} ok="OS cancelada." aoFechar={fechar} aoConcluir={atualizar} />}
      {dialogo === "aprovar" && (
        <Confirmar
          titulo="Aprovar OS"
          mensagem={<p>Aprovar e encerrar a {numeroOS(o.numero)}? Esta ação conclui a ordem.</p>}
          rotuloConfirmar="Aprovar"
          ocupado={ocupado}
          aoConfirmar={() => simples(() => ordens.aprovar(o.numero), "OS aprovada e concluída.")}
          aoFechar={fechar}
        />
      )}
    </>
  );
}

interface PropsForm {
  os: Ordem;
  aoFechar: () => void;
  aoConcluir: () => void;
}

function FormDiagnostico({ os, aoFechar, aoConcluir }: PropsForm) {
  const avisos = useAvisos();
  const [parecer, setParecer] = useState(os.diagnostico);
  const [causa, setCausa] = useState(os.causa_raiz);
  return (
    <FormModal
      titulo="Registrar diagnóstico"
      rotuloEnviar="Registrar"
      aoFechar={aoFechar}
      validar={() => (!parecer.trim() || !causa.trim() ? "Informe o parecer e a causa raiz." : null)}
      aoEnviar={async () => {
        await ordens.diagnosticar(os.numero, parecer.trim(), causa.trim());
        avisos.ok("Diagnóstico registrado.");
        aoConcluir();
      }}
    >
      <CampoAreaTexto rotulo="Parecer técnico" value={parecer} onChange={(e) => setParecer(e.target.value)} maxLength={4000} required />
      <CampoAreaTexto rotulo="Causa raiz" value={causa} onChange={(e) => setCausa(e.target.value)} maxLength={4000} required />
    </FormModal>
  );
}

interface LinhaPeca {
  chave: number;
  descricao: string;
  quantidade: string;
}

function FormReparo({ os, aoFechar, aoConcluir }: PropsForm) {
  const avisos = useAvisos();
  const [h, setH] = useState("");
  const [intervencao, setIntervencao] = useState("");
  const [pecas, setPecas] = useState<LinhaPeca[]>([]);
  const [proxima, setProxima] = useState(1);

  function validar(): string | null {
    const horasNum = lerNumero(h);
    if (Number.isNaN(horasNum) || horasNum < 0) return "Informe as horas trabalhadas (0 ou mais).";
    if (!intervencao.trim()) return "Descreva a intervenção realizada.";
    for (const p of pecas) {
      if (!p.descricao.trim()) return "Toda peça precisa de uma descrição.";
      const q = lerNumero(p.quantidade);
      if (Number.isNaN(q) || q <= 0) return `Quantidade inválida para “${p.descricao}”.`;
    }
    return null;
  }

  return (
    <FormModal
      titulo="Apontar reparo"
      rotuloEnviar="Registrar"
      largo
      aoFechar={aoFechar}
      validar={validar}
      aoEnviar={async () => {
        const lista: Peca[] = pecas.map((p) => ({ descricao: p.descricao.trim(), quantidade: lerNumero(p.quantidade) }));
        await ordens.apontarReparo(os.numero, { horas: lerNumero(h), intervencao: intervencao.trim(), pecas: lista });
        avisos.ok("Reparo registrado.");
        aoConcluir();
      }}
    >
      <CampoTexto rotulo="Horas trabalhadas" inputMode="decimal" value={h} onChange={(e) => setH(e.target.value)} ajuda="Ex.: 1,5" required />
      <CampoAreaTexto rotulo="Intervenção realizada" value={intervencao} onChange={(e) => setIntervencao(e.target.value)} maxLength={4000} required />
      <fieldset className="fieldset-reset">
        <legend>Peças e materiais (opcional)</legend>
        {pecas.map((p, i) => (
          <div key={p.chave} className="form-grade" style={{ alignItems: "end" }}>
            <CampoTexto
              rotulo={`Peça ${i + 1} — descrição`}
              value={p.descricao}
              onChange={(e) => setPecas((l) => l.map((x) => (x.chave === p.chave ? { ...x, descricao: e.target.value } : x)))}
              maxLength={200}
            />
            <div className="linha" style={{ alignItems: "end" }}>
              <div style={{ flex: 1 }}>
                <CampoTexto
                  rotulo="Quantidade"
                  inputMode="decimal"
                  value={p.quantidade}
                  onChange={(e) => setPecas((l) => l.map((x) => (x.chave === p.chave ? { ...x, quantidade: e.target.value } : x)))}
                />
              </div>
              <button type="button" className="btn btn--sec" style={{ marginBottom: "0.9rem" }} onClick={() => setPecas((l) => l.filter((x) => x.chave !== p.chave))}>
                Remover
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          className="btn btn--sec btn--peq"
          onClick={() => {
            setPecas((l) => [...l, { chave: proxima, descricao: "", quantidade: "1" }]);
            setProxima((n) => n + 1);
          }}
        >
          Adicionar peça
        </button>
      </fieldset>
    </FormModal>
  );
}

function FormStatus({ os, opcoes, aoFechar, aoConcluir }: PropsForm & { opcoes: StatusOS[] }) {
  const avisos = useAvisos();
  const [status, setStatus] = useState<StatusOS>(opcoes[0]);
  return (
    <FormModal
      titulo="Alterar status"
      rotuloEnviar="Alterar"
      aoFechar={aoFechar}
      aoEnviar={async () => {
        await ordens.alterarStatus(os.numero, status);
        avisos.ok(`Status alterado para ${status}.`);
        aoConcluir();
      }}
    >
      <p>
        Status atual: <SeloStatus status={os.status} />
      </p>
      <CampoSelecao
        rotulo="Novo status"
        value={status}
        onChange={(e) => setStatus(e.target.value as StatusOS)}
        ajuda="“Reparo Finalizado” exige diagnóstico e ao menos uma intervenção registrados."
      >
        {opcoes.map((s) => (
          <option key={s}>{s}</option>
        ))}
      </CampoSelecao>
    </FormModal>
  );
}

function FormConcluir({ os, aoFechar, aoConcluir }: PropsForm) {
  const avisos = useAvisos();
  const [teste, setTeste] = useState("");
  const [passou, setPassou] = useState(true);
  return (
    <FormModal
      titulo="Conclusão técnica"
      rotuloEnviar="Registrar teste"
      aoFechar={aoFechar}
      validar={() => (!teste.trim() ? "Descreva o teste funcional." : null)}
      aoEnviar={async () => {
        const r = await ordens.concluirTecnicamente(os.numero, teste.trim(), passou);
        avisos.ok(
          r.submetida_a_aprovacao ? "Teste aprovado: OS enviada para aprovação do gestor." : "Teste reprovado: a OS voltou para execução.",
        );
        aoConcluir();
      }}
    >
      <CampoAreaTexto rotulo="Teste funcional realizado" value={teste} onChange={(e) => setTeste(e.target.value)} maxLength={4000} required />
      <label className="campo-marcar">
        <input type="checkbox" checked={passou} onChange={(e) => setPassou(e.target.checked)} />
        <span>O equipamento passou no teste funcional</span>
      </label>
    </FormModal>
  );
}

function FormAtribuir({ os, aoFechar, aoConcluir }: PropsForm) {
  const avisos = useAvisos();
  const { dados, carregando, erro } = useCarregar(() => disponibilidade.listar(true));
  const [tecnicoId, setTecnicoId] = useState("");
  const [confirmar, setConfirmar] = useState(false);
  const escolhido = dados?.find((t) => String(t.id) === tecnicoId);
  const ausente = escolhido?.disponibilidade === "Ausente";

  return (
    <FormModal
      titulo={os.tecnico ? "Reatribuir técnico" : "Atribuir técnico"}
      rotuloEnviar="Atribuir"
      aoFechar={aoFechar}
      validar={() => {
        if (!tecnicoId) return "Escolha um técnico.";
        if (ausente && !confirmar) return "Este técnico está ausente. Marque a confirmação para atribuir mesmo assim.";
        return null;
      }}
      aoEnviar={async () => {
        await ordens.atribuir(os.numero, Number(tecnicoId), ausente && confirmar);
        avisos.ok("Técnico atribuído.");
        aoConcluir();
      }}
    >
      {carregando ? (
        <Carregando texto="Carregando técnicos…" />
      ) : erro ? (
        <p role="alert">{erro}</p>
      ) : (
        <>
          <CampoSelecao rotulo="Técnico" value={tecnicoId} onChange={(e) => { setTecnicoId(e.target.value); setConfirmar(false); }} required>
            <option value="">Selecione…</option>
            {dados?.map((t) => (
              <option key={t.id} value={t.id} disabled={t.id === os.tecnico?.id}>
                {t.nome} — {t.disponibilidade} ({t.carga} OS){t.id === os.tecnico?.id ? " · atual" : ""}
              </option>
            ))}
          </CampoSelecao>
          {ausente && (
            <label className="campo-marcar">
              <input type="checkbox" checked={confirmar} onChange={(e) => setConfirmar(e.target.checked)} />
              <span>Confirmo atribuir a um técnico que está ausente.</span>
            </label>
          )}
        </>
      )}
    </FormModal>
  );
}

function FormApontamento({ os, aoFechar, aoConcluir }: PropsForm) {
  const avisos = useAvisos();
  const [texto, setTexto] = useState("");
  return (
    <FormModal
      titulo="Adicionar observação"
      rotuloEnviar="Adicionar"
      aoFechar={aoFechar}
      validar={() => (!texto.trim() ? "Escreva a observação." : null)}
      aoEnviar={async () => {
        await ordens.apontamento(os.numero, texto.trim());
        avisos.ok("Observação registrada no histórico.");
        aoConcluir();
      }}
    >
      <CampoAreaTexto rotulo="Observação" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={4000} required />
    </FormModal>
  );
}

function FormMotivo({
  titulo,
  rotulo,
  enviar,
  perigo,
  acao,
  ok,
  aoFechar,
  aoConcluir,
}: {
  titulo: string;
  rotulo: string;
  enviar: string;
  perigo?: boolean;
  os: Ordem;
  acao: (motivo: string) => Promise<unknown>;
  ok: string;
  aoFechar: () => void;
  aoConcluir: () => void;
}) {
  const avisos = useAvisos();
  const [motivo, setMotivo] = useState("");
  return (
    <FormModal
      titulo={titulo}
      rotuloEnviar={enviar}
      perigo={perigo}
      aoFechar={aoFechar}
      validar={() => (!motivo.trim() ? "Informe o motivo." : null)}
      aoEnviar={async () => {
        await acao(motivo.trim());
        avisos.ok(ok);
        aoConcluir();
      }}
    >
      <CampoAreaTexto rotulo={rotulo} value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={4000} required />
    </FormModal>
  );
}
