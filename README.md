# Sistema de Gestão de Manutenção de Equipamentos

Aplicação em Python orientada a objetos, com interface de linha de comando (CLI).
Gerencia o ciclo de vida da manutenção: abertura de OS, atribuição, diagnóstico,
reparo, conclusão técnica, aprovação e histórico de serviços.

Explicação das decisões de projeto: veja **DOCUMENTACAO.md**.

## Como executar

```bash
python main.py
```

Requer Python 3.8+ e nenhuma biblioteca externa. Na primeira execução é criado
`dados/dados.json` com dados de exemplo. Para recomeçar do zero, apague esse arquivo.

Usuários de exemplo: **1 – Ana Souza (Gestor)**, **2 – Bruno Lima (Técnico)**,
**3 – Carla Mendes (Técnico)**.

## Estrutura

```
sistema_manutencao/
├── main.py
├── models/                  # classes do domínio (regras de negócio)
│   ├── permissoes.py        # Permissoes
│   ├── cargo.py             # Cargo
│   ├── usuario.py           # Usuario
│   ├── ordem_servico.py     # OrdemServico
│   ├── servico.py           # Servico (serviços executados na OS)
│   ├── peca_material.py     # PecaMaterial
│   ├── equipamento.py       # Equipamento
│   ├── enums.py             # StatusOS, Criticidade, Disponibilidade, TipoServico
│   └── excecoes.py          # RegraNegocioError
├── persistencia/
│   └── repositorio.py       # Repositorio: guarda os objetos e salva/carrega o JSON
├── ui/                      # telas do terminal
│   ├── aplicacao.py         # Aplicacao: login e menu por permissão
│   ├── tela_base.py
│   ├── tela_equipamentos.py
│   ├── tela_usuarios.py
│   ├── tela_ordens.py
│   ├── tela_tecnico.py
│   ├── tela_gestor.py
│   └── entrada.py
└── dados/dados.json         # gerado automaticamente
```

## Classes

```
Usuario ──── cargo ────► Cargo ──── permissoes ────► Permissoes
  id                       id                          ver_equipamentos, ver_os, abrir_os,
  nome                     nome                        ver_disponibilidade, registrar_apontamento,
  cargo                    permissoes                  diagnosticar, apontar_reparo,
  email, escala,                                       atualizar_status, concluir_os,
  disponibilidade                                      gerir_equipamentos, gerir_usuarios,
                                                       atribuir_os, aprovar_os

OrdemServico ──── servicos ────► Servico (1..N)
  numero                           numero (sequencial na OS)
  status                           tipo, descricao, data
  diagnostico                      responsavel (Usuario)
  horas_trabalhadas                horas
  intervencoes_realizadas          pecas (PecaMaterial)
  pecas_utilizadas (PecaMaterial)
  tecnico_atribuido (Usuario)
  equipamento, falha, criticidade, causa_raiz, ...

Equipamento
  id
  nome
  modelo
  ativo (para inativar/reativar)
```

As regras ficam nos métodos das classes. Por exemplo, `OrdemServico.apontar_reparo()`
confere se o usuário tem permissão, se a OS é dele e se o status permite, e então
soma as horas, adiciona a intervenção e as peças e registra um `Servico` no histórico.

## Fluxo de status da OS

Aberta → Atribuída → Em Execução ⇄ Aguardando Peça → Reparo Finalizado
→ Aguardando Aprovação → Concluída  (Cancelada a qualquer momento antes do fim)
