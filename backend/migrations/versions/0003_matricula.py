"""Matrícula: o identificador de login passa a ser a matrícula ``AA999999`` do usuário.

Não altera as revisões 0001 e 0002. Escrita à mão, **idempotente** (cada passo verifica o estado
antes de agir) e **sem apagar dados**:

1. ``usuarios.matricula`` (``VARCHAR(8)``) é criada anulável, preenchida e só então endurecida
   (``NOT NULL``, ``UNIQUE``, ``CHECK`` do formato ``^[A-Z]{2}[0-9]{6}$``).
2. Preenchimento: os três usuários fictícios recebem as matrículas combinadas (Ana ``KM482731``,
   Bruno ``RT095624``, Carla ``VX716309``), reconhecidos pelo login atual (``ana``/``bruno``/
   ``carla``) ou, sem credencial, pelo nome completo da demonstração. Os demais recebem uma
   matrícula **aleatória** (``secrets``), com verificação de unicidade e nova tentativa em colisão.
3. ``credenciais.login`` deixa de ser a chave de entrada: a coluna vira ``login_legado`` (anulável,
   sem unicidade), mantendo o valor antigo apenas como registro. **Senhas (hash), cargos,
   permissões, equipamentos, ordens de serviço e históricos não são tocados.**

``downgrade`` devolve ``login`` (preenchendo com a matrícula em minúsculas as contas criadas depois
desta revisão) e remove ``usuarios.matricula``: as matrículas geradas depois se perdem.

Revision ID: 0003
Revises: 0002
"""

import secrets

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

MATRICULAS_FICTICIAS_POR_LOGIN = {"ana": "KM482731", "bruno": "RT095624", "carla": "VX716309"}
MATRICULAS_FICTICIAS_POR_NOME = {
    "Ana Souza": "KM482731",
    "Bruno Lima": "RT095624",
    "Carla Mendes": "VX716309",
}
_LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DIGITOS = "0123456789"
# Embutido de propósito: uma migração não pode depender de código de aplicação que muda depois.
FORMATO_SQL = "matricula ~ '^[A-Z]{2}[0-9]{6}$'"


def _sortear() -> str:
    return "".join(secrets.choice(_LETRAS) for _ in range(2)) + "".join(
        secrets.choice(_DIGITOS) for _ in range(6)
    )


def _colunas(tabela: str) -> dict[str, dict]:
    return {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def _restricoes(tabela: str) -> set[str]:
    inspetor = sa.inspect(op.get_bind())
    nomes = {u["name"] for u in inspetor.get_unique_constraints(tabela)}
    nomes |= {c["name"] for c in inspetor.get_check_constraints(tabela)}
    return {n for n in nomes if n}


def _preencher_matriculas() -> None:
    ligacao = op.get_bind()
    usuarios = sa.table(
        "usuarios",
        sa.column("id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("matricula", sa.String),
    )
    em_uso = {m for (m,) in ligacao.execute(sa.select(usuarios.c.matricula)) if m is not None}
    # 1) as matrículas combinadas dos usuários fictícios
    reservadas: dict[int, str] = {}
    if "login" in _colunas("credenciais"):
        credenciais = sa.table(
            "credenciais", sa.column("usuario_id", sa.Integer), sa.column("login", sa.String)
        )
        for usuario_id, login in ligacao.execute(
            sa.select(credenciais.c.usuario_id, credenciais.c.login)
        ):
            fixa = MATRICULAS_FICTICIAS_POR_LOGIN.get(str(login).strip().casefold())
            if fixa is not None:
                reservadas[usuario_id] = fixa
    for usuario_id, nome, matricula in ligacao.execute(
        sa.select(usuarios.c.id, usuarios.c.nome, usuarios.c.matricula)
    ):
        fixa = MATRICULAS_FICTICIAS_POR_NOME.get(nome)
        if matricula is None and fixa is not None and usuario_id not in reservadas:
            reservadas[usuario_id] = fixa
    for usuario_id, fixa in reservadas.items():
        atual = ligacao.execute(
            sa.select(usuarios.c.matricula).where(usuarios.c.id == usuario_id)
        ).scalar_one()
        if atual is not None:
            continue  # idempotência: nunca sobrescreve uma matrícula já atribuída
        if fixa in em_uso:
            raise RuntimeError(
                f"A matrícula {fixa} já pertence a outro usuário; resolva antes de migrar."
            )
        ligacao.execute(
            sa.update(usuarios).where(usuarios.c.id == usuario_id).values(matricula=fixa)
        )
        em_uso.add(fixa)
    # 2) as demais: aleatórias, únicas
    pendentes = [
        usuario_id
        for (usuario_id,) in ligacao.execute(
            sa.select(usuarios.c.id).where(usuarios.c.matricula.is_(None)).order_by(usuarios.c.id)
        )
    ]
    reservadas_do_roteiro = set(MATRICULAS_FICTICIAS_POR_LOGIN.values())
    for usuario_id in pendentes:
        for _ in range(1000):
            nova = _sortear()
            if nova not in em_uso and nova not in reservadas_do_roteiro:
                break
        else:  # pragma: no cover - probabilidade desprezível
            raise RuntimeError("Não foi possível gerar uma matrícula livre.")
        ligacao.execute(
            sa.update(usuarios).where(usuarios.c.id == usuario_id).values(matricula=nova)
        )
        em_uso.add(nova)


def upgrade() -> None:
    # --- usuarios.matricula
    if "matricula" not in _colunas("usuarios"):
        op.add_column("usuarios", sa.Column("matricula", sa.String(8), nullable=True))
    _preencher_matriculas()
    if _colunas("usuarios")["matricula"]["nullable"]:
        op.alter_column("usuarios", "matricula", existing_type=sa.String(8), nullable=False)
    restricoes = _restricoes("usuarios")
    if "uq_usuarios_matricula" not in restricoes:
        op.create_unique_constraint("uq_usuarios_matricula", "usuarios", ["matricula"])
    if "ck_usuarios_matricula_formato" not in restricoes:
        op.create_check_constraint(op.f("ck_usuarios_matricula_formato"), "usuarios", FORMATO_SQL)

    # --- credenciais.login -> login_legado (anulável, sem unicidade)
    colunas = _colunas("credenciais")
    if "login" in colunas and "login_legado" not in colunas:
        if "uq_credenciais_login" in _restricoes("credenciais"):
            op.drop_constraint("uq_credenciais_login", "credenciais", type_="unique")
        op.alter_column("credenciais", "login", new_column_name="login_legado", nullable=True)


def downgrade() -> None:
    colunas = _colunas("credenciais")
    if "login_legado" in colunas and "login" not in colunas:
        op.alter_column("credenciais", "login_legado", new_column_name="login", nullable=True)
        op.execute(
            "UPDATE credenciais SET login = lower(u.matricula) "
            "FROM usuarios u WHERE u.id = credenciais.usuario_id AND credenciais.login IS NULL"
        )
        op.alter_column("credenciais", "login", existing_type=sa.String(100), nullable=False)
        if "uq_credenciais_login" not in _restricoes("credenciais"):
            op.create_unique_constraint("uq_credenciais_login", "credenciais", ["login"])
    restricoes = _restricoes("usuarios")
    if "ck_usuarios_matricula_formato" in restricoes:
        op.drop_constraint(op.f("ck_usuarios_matricula_formato"), "usuarios", type_="check")
    if "uq_usuarios_matricula" in restricoes:
        op.drop_constraint("uq_usuarios_matricula", "usuarios", type_="unique")
    if "matricula" in _colunas("usuarios"):
        op.drop_column("usuarios", "matricula")
