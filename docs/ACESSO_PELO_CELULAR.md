# Acesso pelo celular na rede local (desenvolvimento)

Objetivo: abrir o sistema no celular, na mesma rede Wi-Fi do computador, **sem enfraquecer a autenticação** e
**sem expor o banco**. Nada aqui é hospedagem pública.

## Princípios

1. **Mesma origem sempre que possível.** O frontend (Vite) serve a interface e **faz proxy** de `/api` para a API.
   O celular fala só com o frontend (`http://<IP-do-PC>:5173`); para o navegador, interface e API são a mesma
   origem: o cookie `SameSite=Lax` e o CSRF funcionam sem CORS.
2. **Sem `*` com credenciais.** Se o proxy não for usado, a origem do frontend vai em `MANUTENCAO_API_ORIGENS` (uma
   por vez, explícita). A API recusa `*`.
3. **O PostgreSQL continua em `localhost`.** Nunca abra a porta 5432 no firewall nem altere `listen_addresses`.
4. **CSRF e cookies não são desligados** para "fazer funcionar".

## Passo a passo

1. Descubra o IP do computador na rede (PowerShell): `ipconfig` → "Adaptador de Rede sem Fio" → "Endereço IPv4"
   (ex.: `192.168.0.10`). Computador e celular precisam estar na **mesma rede**; redes de convidados costumam
   isolar dispositivos.
2. API (a partir de `backend/`): **escuta só em `127.0.0.1` por padrão**. Com o proxy do frontend isso basta, porque
   o proxy roda no computador. Só use `--rede` se for acessar a API diretamente pelo celular:
   `python -m manutencao.composicao.servidor --rede`.
3. Frontend (Fase 05, `frontend/`, já com este proxy em `vite.config.ts`): o servidor de desenvolvimento deve escutar na rede (`vite --host`) e ter o proxy:

   ```ts
   // vite.config.ts (implementado; use changeOrigin: false)
   export default defineConfig({
     server: { host: true, port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
   });
   ```

   O navegador do celular abre `http://192.168.0.10:5173`. Com o proxy padrão do Vite (`changeOrigin` desligado) o
   cabeçalho `Host` continua o do frontend e o `Origin` bate com ele: a verificação de origem da API aceita. Se
   você ligar `changeOrigin: true`, acrescente `http://192.168.0.10:5173` a `MANUTENCAO_API_ORIGENS`.
4. Se a API for acessada **direto** (sem proxy) a partir de outra origem: em `backend/.env`,
   `MANUTENCAO_API_ORIGENS=http://192.168.0.10:5173` e o frontend usa `credentials: "include"`. Prefira o proxy.
5. **Firewall do Windows:** na primeira vez o Windows pergunta se permite o Node/Python em redes privadas. Permita
   **somente em "Rede privada"**, nunca em "Pública", e só para o frontend (5173) — e para a API (8000) apenas se usar
   `--rede`. Não desative o firewall e não crie regras para a porta 5432.

## Limitações e riscos (não minimize)

- **HTTP na rede local não é HTTPS.** O tráfego (inclusive a senha digitada no login) trafega em texto claro dentro
  da rede Wi-Fi: qualquer dispositivo da mesma rede pode observá-lo. Use rede doméstica confiável, **nunca** Wi-Fi
  público, e senhas que você não reutiliza. O cookie, em HTTP, não pode ter o atributo `Secure`
  (`MANUTENCAO_API_COOKIE_SECURE=false`); com HTTPS (proxy reverso com certificado) ligue-o para `true`.
- Navegadores móveis podem tratar `http://<IP>` como contexto não seguro (sem alguns recursos de PWA/geolocalização).
- O endereço IP pode mudar quando o roteador reatribui; repita o passo 1.
- `--rede` e o acesso por IP são para **desenvolvimento e demonstração**. Não é um modo de produção.

## Verificação rápida

No celular: `http://192.168.0.10:5173` abre a tela de login; após o login, a aba de rede do computador (ou o log da
API) mostra as requisições `/api/v1/...` com o cookie `manutencao_sessao`. De fora da rede, nada deve responder.
Para confirmar que o banco não está exposto, do celular a porta 5432 do IP do computador **não** deve conectar.
