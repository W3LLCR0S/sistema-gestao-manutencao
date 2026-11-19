import { useState } from "react";
import { mensagemDeErro } from "../api/cliente";
import { cargos } from "../api/servicos";
import type { Cargo, Permissao, PermissaoInfo } from "../api/tipos";
import { useAvisos } from "../componentes/Avisos";
import { Carregando, ErroCarga } from "../componentes/Estados";
import { useCarregar } from "../utilitarios/useCarregar";

export function Cargos() {
  const { dados, carregando, erro, recarregar } = useCarregar(() =>
    Promise.all([cargos.listar(), cargos.catalogo()]),
  );
  if (carregando && !dados) return <Carregando />;
  if (erro && !dados) return <ErroCarga mensagem={erro} aoTentar={recarregar} />;
  if (!dados) return null;
  const [lista, catalogo] = dados;
  return (
    <>
      <div className="pagina-cab">
        <div>
          <h1>Cargos e permissões</h1>
          <p className="pagina-cab__sub">As permissões do cargo valem para todos os usuários que o ocupam.</p>
        </div>
      </div>
      {lista.map((c) => (
        <CartaoCargo key={c.id} cargo={c} catalogo={catalogo} aoSalvar={recarregar} />
      ))}
    </>
  );
}

function CartaoCargo({ cargo, catalogo, aoSalvar }: { cargo: Cargo; catalogo: PermissaoInfo[]; aoSalvar: () => void }) {
  const avisos = useAvisos();
  const [marcadas, setMarcadas] = useState<Set<Permissao>>(new Set(cargo.permissoes));
  const [salvando, setSalvando] = useState(false);
  const alterado =
    marcadas.size !== cargo.permissoes.length || cargo.permissoes.some((p) => !marcadas.has(p));

  function alternar(p: Permissao) {
    setMarcadas((atual) => {
      const novo = new Set(atual);
      if (novo.has(p)) novo.delete(p);
      else novo.add(p);
      return novo;
    });
  }

  async function salvar() {
    setSalvando(true);
    try {
      await cargos.definirPermissoes(cargo.id, catalogo.map((c) => c.nome).filter((n) => marcadas.has(n)));
      avisos.ok(`Permissões de “${cargo.nome}” salvas.`);
      aoSalvar();
    } catch (ex) {
      avisos.erro(mensagemDeErro(ex));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section className="cartao" aria-labelledby={`cargo-${cargo.id}`}>
      <h2 id={`cargo-${cargo.id}`}>{cargo.nome}</h2>
      <fieldset className="fieldset-reset">
        <legend>Permissões</legend>
        <div className="permissoes">
          {catalogo.map((p) => (
            <label key={p.nome} className="campo-marcar">
              <input type="checkbox" checked={marcadas.has(p.nome)} onChange={() => alternar(p.nome)} />
              <span>{p.descricao}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="acoes acoes--inicio">
        <button type="button" className="btn" disabled={!alterado || salvando} onClick={salvar}>
          {salvando ? "Salvando…" : "Salvar permissões"}
        </button>
        {alterado && (
          <button type="button" className="btn btn--sec" onClick={() => setMarcadas(new Set(cargo.permissoes))}>
            Descartar
          </button>
        )}
      </div>
    </section>
  );
}
