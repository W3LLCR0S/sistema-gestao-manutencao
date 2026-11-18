import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { mensagemDeErro } from "../api/cliente";
import { cargos, usuarios } from "../api/servicos";
import type { Disponibilidade, Papel, Usuario } from "../api/tipos";
import { useAuth } from "../auth/Autenticacao";
import { useAvisos } from "../componentes/Avisos";
import { CampoSelecao, CampoTexto } from "../componentes/Campos";
import { Carregando, ErroCarga, Vazio } from "../componentes/Estados";
import { FormModal } from "../componentes/FormModal";
import { Confirmar, Modal } from "../componentes/Modal";
import { SeloAtivo, SeloDisponibilidade } from "../componentes/Selos";
import { useCarregar } from "../utilitarios/useCarregar";

type Dialogo =
  | { tipo: "novo" }
  | { tipo: "criado"; usuario: Usuario }
  | { tipo: "detalhe"; id: number }
  | { tipo: "editar"; item: Usuario }
  | { tipo: "credencial"; item: Usuario }
  | { tipo: "desativar"; item: Usuario }
  | { tipo: "excluir"; item: Usuario }
  | null;

export function Usuarios() {
  const { usuario: eu } = useAuth();
  const avisos = useAvisos();
  const [filtroAtivo, setFiltroAtivo] = useState<"" | "true" | "false">("");
  const [filtroPapel, setFiltroPapel] = useState<"" | Papel>("");
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  // A pesquisa (por matrícula, nome ou e-mail) é feita pelo servidor, com uma pequena espera ao digitar.
  useEffect(() => {
    const t = window.setTimeout(() => setBuscaAplicada(busca.trim()), 300);
    return () => window.clearTimeout(t);
  }, [busca]);
  const { dados, carregando, erro, recarregar } = useCarregar(
    () => usuarios.listar(filtroAtivo === "" ? undefined : filtroAtivo === "true", filtroPapel || undefined, buscaAplicada),
    [filtroAtivo, filtroPapel, buscaAplicada],
  );
  const catalogo = useCarregar(() => cargos.listar());
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [ocupado, setOcupado] = useState(false);

  const itens = dados?.itens ?? [];

  async function executar(acao: () => Promise<unknown>, sucesso: string) {
    setOcupado(true);
    try {
      await acao();
      avisos.ok(sucesso);
      setDialogo(null);
      recarregar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
      setDialogo(null);
    } finally {
      setOcupado(false);
    }
  }

  const detalhe = dialogo?.tipo === "detalhe" ? dados?.itens.find((u) => u.id === dialogo.id) : undefined;

  return (
    <>
      <div className="pagina-cab">
        <div>
          <h1>Usuários</h1>
          <p className="pagina-cab__sub">{dados ? `${dados.total} usuário(s)` : "Gestores e técnicos"}</p>
        </div>
        <button type="button" className="btn" onClick={() => setDialogo({ tipo: "novo" })} disabled={!catalogo.dados}>
          <Plus aria-hidden="true" /> Novo usuário
        </button>
      </div>

      <div className="cartao">
        <div className="filtros">
          <CampoTexto rotulo="Buscar por matrícula, nome ou e-mail" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
          <CampoSelecao rotulo="Papel" value={filtroPapel} onChange={(e) => setFiltroPapel(e.target.value as "" | Papel)}>
            <option value="">Todos</option>
            <option value="Gestor">Gestor</option>
            <option value="Técnico">Técnico</option>
          </CampoSelecao>
          <CampoSelecao rotulo="Situação" value={filtroAtivo} onChange={(e) => setFiltroAtivo(e.target.value as "" | "true" | "false")}>
            <option value="">Todos</option>
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
          </CampoSelecao>
        </div>
      </div>

      {carregando && !dados ? (
        <Carregando />
      ) : erro && !dados ? (
        <ErroCarga mensagem={erro} aoTentar={recarregar} />
      ) : itens.length === 0 ? (
        <Vazio titulo="Nenhum usuário encontrado">Ajuste a busca ou os filtros.</Vazio>
      ) : (
        <div className="tabela-wrap">
          <table className="tabela-resp">
            <thead>
              <tr>
                <th>Matrícula</th>
                <th>Nome</th>
                <th>Papel</th>
                <th>Cargo</th>
                <th>Disponibilidade</th>
                <th>Situação</th>
                <th>
                  <span className="sr-only">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {itens.map((u) => (
                <tr key={u.id}>
                  <td data-rotulo="Matrícula">
                    <code className="matricula">{u.matricula}</code>
                  </td>
                  <td data-rotulo="Nome">
                    <button type="button" className="btn-link" onClick={() => setDialogo({ tipo: "detalhe", id: u.id })}>
                      {u.nome}
                    </button>
                    {u.id === eu?.id && <small> (você)</small>}
                  </td>
                  <td data-rotulo="Papel">{u.papel}</td>
                  <td data-rotulo="Cargo">{u.cargo.nome}</td>
                  <td data-rotulo="Disponibilidade">{u.papel === "Técnico" ? <SeloDisponibilidade valor={u.disponibilidade} /> : "—"}</td>
                  <td data-rotulo="Situação">
                    <SeloAtivo ativo={u.ativo} />
                  </td>
                  <td className="celula-acoes">
                    <button type="button" className="btn btn--sec btn--peq" onClick={() => setDialogo({ tipo: "detalhe", id: u.id })}>
                      Detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialogo?.tipo === "novo" && catalogo.dados && (
        <FormularioNovo
          cargosLista={catalogo.dados}
          // não sobrepõe a confirmação (com a matrícula) aberta logo após o cadastro
          aoFechar={() => setDialogo((atual) => (atual?.tipo === "criado" ? atual : null))}
          aoSalvar={async (d) => {
            const criado = await usuarios.criar(d);
            recarregar();
            setDialogo({ tipo: "criado", usuario: criado });
          }}
        />
      )}

      {dialogo?.tipo === "criado" && (
        <Modal titulo="Usuário cadastrado" aoFechar={() => setDialogo(null)}>
          <p>
            <strong>{dialogo.usuario.nome}</strong> foi cadastrado(a). A matrícula foi gerada pelo sistema e é usada no login:
          </p>
          <p className="matricula-destaque" aria-label="Matrícula gerada">
            {dialogo.usuario.matricula}
          </p>
          <p className="campo__ajuda">
            {dialogo.usuario.ativo ? "Anote-a e entregue ao funcionário. " : ""}A matrícula não pode ser alterada. Ela pode ser consultada
            depois na lista de usuários.
          </p>
          <div className="acoes">
            <button type="button" className="btn" onClick={() => setDialogo(null)} autoFocus>
              Fechar
            </button>
          </div>
        </Modal>
      )}

      {detalhe && (
        <Modal titulo={detalhe.nome} aoFechar={() => setDialogo(null)} largo>
          <dl className="detalhes">
            <div>
              <dt>Matrícula</dt>
              <dd>
                <code className="matricula">{detalhe.matricula}</code>
              </dd>
            </div>
            <div>
              <dt>E-mail</dt>
              <dd>{detalhe.email || "—"}</dd>
            </div>
            <div>
              <dt>Escala</dt>
              <dd>{detalhe.escala || "—"}</dd>
            </div>
            <div>
              <dt>Papel</dt>
              <dd>{detalhe.papel}</dd>
            </div>
            <div>
              <dt>Cargo</dt>
              <dd>{detalhe.cargo.nome}</dd>
            </div>
            <div>
              <dt>Situação</dt>
              <dd>
                <SeloAtivo ativo={detalhe.ativo} />
              </dd>
            </div>
            <div>
              <dt>Disponibilidade (manual)</dt>
              <dd>{detalhe.disponibilidade}</dd>
            </div>
            <div className="largo">
              <dt>Permissões efetivas</dt>
              <dd>{detalhe.permissoes.length ? detalhe.permissoes.join(", ") : "Nenhuma (usuário inativo)"}</dd>
            </div>
          </dl>
          <DetalhesAcoes
            usuario={detalhe}
            cargosLista={catalogo.dados ?? []}
            aoAlterar={recarregar}
            aoEscolher={(d) => setDialogo(d)}
          />
        </Modal>
      )}

      {dialogo?.tipo === "editar" && (
        <FormularioEdicao
          item={dialogo.item}
          aoFechar={() => setDialogo(null)}
          aoSalvar={async (d) => {
            await usuarios.atualizar(dialogo.item.id, d);
            avisos.ok("Usuário atualizado.");
            recarregar();
          }}
        />
      )}
      {dialogo?.tipo === "credencial" && (
        <FormularioCredencial
          item={dialogo.item}
          aoFechar={() => setDialogo(null)}
          aoSalvar={async (senha) => {
            await usuarios.definirCredencial(dialogo.item.id, senha);
            avisos.ok("Senha definida. As sessões do usuário foram encerradas.");
            recarregar();
          }}
        />
      )}
      {dialogo?.tipo === "desativar" && (
        <Confirmar
          titulo={dialogo.item.ativo ? "Desativar usuário" : "Reativar usuário"}
          mensagem={
            dialogo.item.ativo ? (
              <p>
                Desativar <strong>{dialogo.item.nome}</strong>? O acesso é bloqueado e as sessões são encerradas. A API recusa se
                for o último gestor apto ou se houver OS ativas atribuídas.
              </p>
            ) : (
              <p>
                Reativar <strong>{dialogo.item.nome}</strong>?
              </p>
            )
          }
          rotuloConfirmar={dialogo.item.ativo ? "Desativar" : "Reativar"}
          perigo={dialogo.item.ativo}
          ocupado={ocupado}
          aoConfirmar={() =>
            executar(
              () => (dialogo.item.ativo ? usuarios.desativar(dialogo.item.id) : usuarios.reativar(dialogo.item.id)),
              dialogo.item.ativo ? "Usuário desativado." : "Usuário reativado.",
            )
          }
          aoFechar={() => setDialogo(null)}
        />
      )}
      {dialogo?.tipo === "excluir" && (
        <Confirmar
          titulo="Excluir usuário"
          mensagem={
            <p>
              Excluir <strong>{dialogo.item.nome}</strong> definitivamente? Só é possível se não houver histórico em OS; caso
              contrário, desative-o.
            </p>
          }
          rotuloConfirmar="Excluir"
          perigo
          ocupado={ocupado}
          aoConfirmar={() => executar(() => usuarios.excluir(dialogo.item.id), "Usuário excluído.")}
          aoFechar={() => setDialogo(null)}
        />
      )}
    </>
  );
}

function DetalhesAcoes({
  usuario,
  cargosLista,
  aoAlterar,
  aoEscolher,
}: {
  usuario: Usuario;
  cargosLista: { id: number; nome: string }[];
  aoAlterar: () => void;
  aoEscolher: (d: Dialogo) => void;
}) {
  const avisos = useAvisos();
  const [cargoId, setCargoId] = useState(usuario.cargo.id);
  const [papel, setPapel] = useState<Papel>(usuario.papel);
  const [disp, setDisp] = useState<Disponibilidade>(usuario.disponibilidade);

  async function aplicar(acao: () => Promise<unknown>, ok: string) {
    try {
      await acao();
      avisos.ok(ok);
      aoAlterar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
    }
  }

  return (
    <>
      <h3 style={{ marginTop: "1.25rem" }}>Cargo, papel e disponibilidade</h3>
      <div className="form-grade">
        <div>
          <CampoSelecao rotulo="Cargo" value={cargoId} onChange={(e) => setCargoId(Number(e.target.value))}>
            {cargosLista.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </CampoSelecao>
          <button type="button" className="btn btn--sec btn--peq" disabled={cargoId === usuario.cargo.id} onClick={() => aplicar(() => usuarios.alterarCargo(usuario.id, cargoId), "Cargo alterado.")}>
            Aplicar cargo
          </button>
        </div>
        <div>
          <CampoSelecao rotulo="Papel" value={papel} onChange={(e) => setPapel(e.target.value as Papel)}>
            <option value="Gestor">Gestor</option>
            <option value="Técnico">Técnico</option>
          </CampoSelecao>
          <button type="button" className="btn btn--sec btn--peq" disabled={papel === usuario.papel} onClick={() => aplicar(() => usuarios.alterarPapel(usuario.id, papel), "Papel alterado.")}>
            Aplicar papel
          </button>
        </div>
        {usuario.papel === "Técnico" && (
          <div>
            <CampoSelecao rotulo="Disponibilidade manual" value={disp} onChange={(e) => setDisp(e.target.value as Disponibilidade)}>
              <option value="Disponível">Disponível</option>
              <option value="Ausente">Ausente</option>
            </CampoSelecao>
            <button
              type="button"
              className="btn btn--sec btn--peq"
              disabled={disp === usuario.disponibilidade || disp === "Em atendimento"}
              onClick={() => aplicar(() => usuarios.alterarDisponibilidade(usuario.id, disp), "Disponibilidade alterada.")}
            >
              Aplicar disponibilidade
            </button>
          </div>
        )}
      </div>
      <div className="acoes acoes--inicio">
        <button type="button" className="btn btn--sec" onClick={() => aoEscolher({ tipo: "editar", item: usuario })}>
          Editar dados
        </button>
        <button type="button" className="btn btn--sec" onClick={() => aoEscolher({ tipo: "credencial", item: usuario })}>
          Definir senha
        </button>
        <button type="button" className="btn btn--sec" onClick={() => aoEscolher({ tipo: "desativar", item: usuario })}>
          {usuario.ativo ? "Desativar" : "Reativar"}
        </button>
        <button type="button" className="btn btn--perigo" onClick={() => aoEscolher({ tipo: "excluir", item: usuario })}>
          Excluir
        </button>
      </div>
    </>
  );
}

function FormularioNovo({
  cargosLista,
  aoFechar,
  aoSalvar,
}: {
  cargosLista: { id: number; nome: string }[];
  aoFechar: () => void;
  aoSalvar: (d: { nome: string; cargo_id: number; papel: Papel; email: string; escala: string; senha?: string }) => Promise<void>;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [escala, setEscala] = useState("");
  const [cargoId, setCargoId] = useState(cargosLista[0]?.id ?? 0);
  const [papel, setPapel] = useState<Papel>("Técnico");
  const [senha, setSenha] = useState("");
  return (
    <FormModal
      titulo="Novo usuário"
      rotuloEnviar="Cadastrar"
      largo
      aoFechar={aoFechar}
      validar={() => {
        if (!nome.trim()) return "Informe o nome.";
        return null;
      }}
      aoEnviar={() =>
        aoSalvar({
          nome: nome.trim(),
          cargo_id: cargoId,
          papel,
          email: email.trim(),
          escala: escala.trim(),
          ...(senha ? { senha } : {}),
        })
      }
    >
      <div className="form-grade">
        <CampoTexto rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={200} required />
        <CampoTexto rotulo="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={254} />
        <CampoSelecao rotulo="Cargo" value={cargoId} onChange={(e) => setCargoId(Number(e.target.value))}>
          {cargosLista.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </CampoSelecao>
        <CampoSelecao rotulo="Papel" value={papel} onChange={(e) => setPapel(e.target.value as Papel)}>
          <option value="Técnico">Técnico</option>
          <option value="Gestor">Gestor</option>
        </CampoSelecao>
        <CampoTexto rotulo="Escala" value={escala} onChange={(e) => setEscala(e.target.value)} maxLength={100} ajuda="Ex.: Seg–Sex 8h–17h" />
        <span />
        <CampoTexto rotulo="Senha de acesso (opcional)" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="new-password" ajuda="Mínimo de 10 caracteres. Sem senha, o acesso é definido depois." />
        <p className="campo__ajuda" style={{ gridColumn: "1 / -1" }}>
          A matrícula (duas letras e seis números) é gerada automaticamente ao cadastrar e será exibida na confirmação.
        </p>
      </div>
    </FormModal>
  );
}

function FormularioEdicao({
  item,
  aoFechar,
  aoSalvar,
}: {
  item: Usuario;
  aoFechar: () => void;
  aoSalvar: (d: { nome: string; email: string; escala: string }) => Promise<void>;
}) {
  const [nome, setNome] = useState(item.nome);
  const [email, setEmail] = useState(item.email);
  const [escala, setEscala] = useState(item.escala);
  return (
    <FormModal
      titulo="Editar dados"
      rotuloEnviar="Salvar"
      aoFechar={aoFechar}
      validar={() => (!nome.trim() ? "Informe o nome." : null)}
      aoEnviar={() => aoSalvar({ nome: nome.trim(), email: email.trim(), escala: escala.trim() })}
    >
      <CampoTexto rotulo="Nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={200} required />
      <CampoTexto rotulo="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={254} />
      <CampoTexto rotulo="Escala" value={escala} onChange={(e) => setEscala(e.target.value)} maxLength={100} />
    </FormModal>
  );
}

function FormularioCredencial({
  item,
  aoFechar,
  aoSalvar,
}: {
  item: Usuario;
  aoFechar: () => void;
  aoSalvar: (senha: string) => Promise<void>;
}) {
  const [senha, setSenha] = useState("");
  return (
    <FormModal
      titulo={`Senha — ${item.nome}`}
      rotuloEnviar="Definir"
      aoFechar={aoFechar}
      validar={() => (!senha ? "Informe a nova senha." : null)}
      aoEnviar={() => aoSalvar(senha)}
    >
      <p className="campo__ajuda">
        Matrícula de acesso: <code className="matricula">{item.matricula}</code> (não muda).
      </p>
      <CampoTexto rotulo="Nova senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="new-password" required />
    </FormModal>
  );
}
