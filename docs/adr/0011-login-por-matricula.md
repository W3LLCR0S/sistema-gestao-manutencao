# ADR-0011 — Login por matrícula

- **Status:** implementada na branch `feat/autenticacao-matricula` (altera a identificação da [ADR-0010](0010-autenticacao-e-sessao.md); hash Argon2id, cookie `HttpOnly`, CSRF, sessões, limite de tentativas e permissões não mudam).
- **Migração:** `0003_matricula` (as revisões 0001 e 0002 não foram tocadas).

## Decisão

O usuário entra com **matrícula + senha**. Não há mais nome de login.

- **Formato:** `AA999999` — duas letras maiúsculas A-Z e seis dígitos (ex.: `KM482731`), validado no domínio (`domain/matricula.py`), no banco (`CHECK ck_usuarios_matricula_formato`) e na tela.
- **Geração:** só pelo sistema, com `secrets.choice` (fonte criptográfica). `ServicoDeUsuarios.cadastrar` sorteia, consulta `matricula_existe` e sorteia de novo em colisão (até 100 candidatas); se uma corrida fizer a restrição `UNIQUE` (`uq_usuarios_matricula`) falhar, a gravação roda em *savepoint* e o cadastro tenta outra matrícula (até 5 vezes).
- **Imutável:** `Usuario.matricula` é somente leitura e só é atribuída uma vez; nenhuma rota, caso de uso ou `salvar` a altera; a API recusa o campo na entrada (422).
- **Onde fica:** `usuarios.matricula` (não em `credenciais`), pois todo usuário a tem, com ou sem senha. `credenciais` guarda só o hash; a coluna antiga `login` virou `login_legado` (anulável, sem unicidade, nunca usada para entrar).
- **Login:** matrícula malformada, desconhecida, senha errada e usuário inativo recebem a **mesma** resposta (401) e o mesmo custo de hash. O nome antigo (`ana`…) falha como matrícula inválida; enviar o campo `login` é 422. A matrícula **não é senha**: a senha não pode ser nem conter a matrícula. Limite de tentativas por `IP|matrícula`.
- **Exposição:** a matrícula não é segredo; aparece na confirmação do cadastro, na listagem e nos detalhes (só o Gestor, `gerir_usuarios`) e em "Minha conta". Pesquisa: `GET /usuarios?busca=` (matrícula, nome ou e-mail).

## Migração dos dados existentes

Ana `KM482731`, Bruno `RT095624`, Carla `VX716309` (reconhecidos pelo login anterior ou, sem credencial, pelo nome da demonstração); demais usuários recebem matrícula aleatória única. Cada passo verifica o estado antes de agir (idempotente) e nada é apagado: senhas (hash), cargos, permissões, equipamentos, OS, históricos e sessões permanecem. `downgrade` restaura `login` (matrícula em minúsculas para contas criadas depois) e remove `matricula`.

## Consequências

- Sessões existentes continuam válidas; quem entra usa a nova identificação.
- Quem administra consulta matrículas com `python -m manutencao.composicao.banco usuarios`.
- Recuperação de senha continua administrativa (`definir-acesso --matricula`).
