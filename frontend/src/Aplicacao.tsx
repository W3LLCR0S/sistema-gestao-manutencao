import { Link, Route, Routes } from "react-router-dom";
import { RotaProtegida } from "./auth/Autenticacao";
import { Layout } from "./componentes/Layout";
import { Cargos } from "./paginas/Cargos";
import { Equipamentos } from "./paginas/Equipamentos";
import { Login } from "./paginas/Login";
import { NovaOrdem } from "./paginas/NovaOrdem";
import { OrdemDetalhe } from "./paginas/OrdemDetalhe";
import { Ordens } from "./paginas/Ordens";
import { Painel } from "./paginas/Painel";
import { AlterarSenha } from "./paginas/AlterarSenha";
import { Usuarios } from "./paginas/Usuarios";

function NaoEncontrada() {
  return (
    <div className="vazio">
      <h2>Página não encontrada</h2>
      <p>
        <Link to="/">Voltar ao painel</Link>
      </p>
    </div>
  );
}

export function Aplicacao() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RotaProtegida>
            <Layout />
          </RotaProtegida>
        }
      >
        <Route index element={<RotaProtegida permissao="ver_os"><Painel /></RotaProtegida>} />
        <Route path="ordens" element={<RotaProtegida permissao="ver_os"><Ordens /></RotaProtegida>} />
        <Route path="ordens/nova" element={<RotaProtegida permissao="abrir_os"><NovaOrdem /></RotaProtegida>} />
        <Route path="ordens/:numero" element={<RotaProtegida permissao="ver_os"><OrdemDetalhe /></RotaProtegida>} />
        <Route path="equipamentos" element={<RotaProtegida permissao="ver_equipamentos"><Equipamentos /></RotaProtegida>} />
        <Route path="usuarios" element={<RotaProtegida permissao="gerir_usuarios"><Usuarios /></RotaProtegida>} />
        <Route path="cargos" element={<RotaProtegida permissao="gerir_usuarios"><Cargos /></RotaProtegida>} />
        <Route path="senha" element={<AlterarSenha />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  );
}
