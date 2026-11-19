import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Aplicacao } from "./Aplicacao";
import { ProvedorAutenticacao } from "./auth/Autenticacao";
import { ProvedorAvisos } from "./componentes/Avisos";
import "./estilos/global.css";

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <BrowserRouter>
      <ProvedorAvisos>
        <ProvedorAutenticacao>
          <Aplicacao />
        </ProvedorAutenticacao>
      </ProvedorAvisos>
    </BrowserRouter>
  </StrictMode>,
);
