"""Esquema inicial: sequências, cargos, usuários, equipamentos e ordens de serviço.

Escrito à mão e **independente do código atual** (os valores permitidos estão literais): uma
migração antiga deve continuar reproduzindo o mesmo esquema mesmo que os enums do domínio mudem.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

PERMISSOES = (
    "ver_equipamentos",
    "ver_os",
    "abrir_os",
    "ver_disponibilidade",
    "registrar_apontamento",
    "diagnosticar",
    "apontar_reparo",
    "atualizar_status",
    "concluir_os",
    "gerir_equipamentos",
    "gerir_usuarios",
    "atribuir_os",
    "aprovar_os",
)
PAPEIS = ("Gestor", "Técnico")
DISPONIBILIDADES = ("Disponível", "Em atendimento", "Ausente")
STATUS = (
    "Aberta",
    "Atribuída",
    "Em Execução",
    "Aguardando Peça",
    "Reparo Finalizado",
    "Aguardando Aprovação",
    "Concluída",
    "Cancelada",
)
CRITICIDADES = ("Baixa", "Média", "Alta", "Crítica")
TIPOS_SERVICO = (
    "Abertura",
    "Atribuição",
    "Reatribuição",
    "Diagnóstico",
    "Reparo",
    "Mudança de status",
    "Apontamento",
    "Teste funcional",
    "Conclusão técnica",
    "Encerramento",
    "Reprovação",
    "Cancelamento",
)
SEQUENCIAS = ("cargo", "equipamento", "usuario", "ordem_servico")


def _em(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


def upgrade() -> None:
    op.create_table(
        "sequencias",
        sa.Column("entidade", sa.String(40), nullable=False),
        sa.Column("ultimo", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("entidade", name="pk_sequencias"),
        sa.CheckConstraint("ultimo >= 0", name="ck_sequencias_ultimo_nao_negativo"),
    )
    op.bulk_insert(
        sa.table(
            "sequencias", sa.column("entidade", sa.String), sa.column("ultimo", sa.BigInteger)
        ),
        [{"entidade": nome, "ultimo": 0} for nome in SEQUENCIAS],
    )

    op.create_table(
        "cargos",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cargos"),
    )
    op.create_table(
        "cargo_permissoes",
        sa.Column("cargo_id", sa.Integer(), nullable=False),
        sa.Column("permissao", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["cargo_id"],
            ["cargos.id"],
            name="fk_cargo_permissoes_cargo_id_cargos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("cargo_id", "permissao", name="pk_cargo_permissoes"),
        sa.CheckConstraint(
            _em("permissao", PERMISSOES), name="ck_cargo_permissoes_permissao_valida"
        ),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("cargo_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("escala", sa.String(100), nullable=False),
        sa.Column("disponibilidade", sa.String(20), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cargo_id"], ["cargos.id"], name="fk_usuarios_cargo_id_cargos", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.CheckConstraint(_em("papel", PAPEIS), name="ck_usuarios_papel_valido"),
        sa.CheckConstraint(
            _em("disponibilidade", DISPONIBILIDADES), name="ck_usuarios_disponibilidade_valida"
        ),
    )
    op.create_index("ix_usuarios_cargo_id", "usuarios", ["cargo_id"])

    op.create_table(
        "equipamentos",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("modelo", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_equipamentos"),
    )

    op.create_table(
        "ordens_servico",
        sa.Column("numero", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("equipamento_id", sa.Integer(), nullable=False),
        sa.Column("equipamento_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("falha", sa.Text(), nullable=False),
        sa.Column("criticidade", sa.String(20), nullable=False),
        sa.Column("aberta_por_id", sa.Integer(), nullable=False),
        sa.Column("aberta_por_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("data_abertura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("tecnico_id", sa.Integer(), nullable=True),
        sa.Column("tecnico_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("diagnostico", sa.Text(), nullable=False),
        sa.Column("causa_raiz", sa.Text(), nullable=False),
        sa.Column("teste_funcional", sa.Text(), nullable=False),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=False),
        sa.Column("data_conclusao", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("numero", name="pk_ordens_servico"),
        sa.CheckConstraint(_em("status", STATUS), name="ck_ordens_servico_status_valido"),
        sa.CheckConstraint(
            _em("criticidade", CRITICIDADES), name="ck_ordens_servico_criticidade_valida"
        ),
    )
    op.create_index("ix_ordens_servico_status", "ordens_servico", ["status"])
    op.create_index("ix_ordens_servico_equipamento_id", "ordens_servico", ["equipamento_id"])
    op.create_index("ix_ordens_servico_tecnico_id", "ordens_servico", ["tecnico_id"])
    op.create_index("ix_ordens_servico_aberta_por_id", "ordens_servico", ["aberta_por_id"])

    op.create_table(
        "servicos_os",
        sa.Column("os_numero", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), nullable=True),
        sa.Column("responsavel_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("data", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horas", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(
            ["os_numero"],
            ["ordens_servico.numero"],
            name="fk_servicos_os_os_numero_ordens_servico",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("os_numero", "numero", name="pk_servicos_os"),
        sa.CheckConstraint(_em("tipo", TIPOS_SERVICO), name="ck_servicos_os_tipo_valido"),
        sa.CheckConstraint("horas >= 0", name="ck_servicos_os_horas_nao_negativas"),
    )
    op.create_index("ix_servicos_os_responsavel_id", "servicos_os", ["responsavel_id"])

    op.create_table(
        "pecas_servico",
        sa.Column("os_numero", sa.Integer(), nullable=False),
        sa.Column("servico_numero", sa.Integer(), nullable=False),
        sa.Column("posicao", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(
            ["os_numero", "servico_numero"],
            ["servicos_os.os_numero", "servicos_os.numero"],
            name="fk_pecas_servico_os_numero_servicos_os",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("os_numero", "servico_numero", "posicao", name="pk_pecas_servico"),
        sa.CheckConstraint("quantidade > 0", name="ck_pecas_servico_quantidade_positiva"),
    )


def downgrade() -> None:
    op.drop_table("pecas_servico")
    op.drop_index("ix_servicos_os_responsavel_id", table_name="servicos_os")
    op.drop_table("servicos_os")
    op.drop_index("ix_ordens_servico_aberta_por_id", table_name="ordens_servico")
    op.drop_index("ix_ordens_servico_tecnico_id", table_name="ordens_servico")
    op.drop_index("ix_ordens_servico_equipamento_id", table_name="ordens_servico")
    op.drop_index("ix_ordens_servico_status", table_name="ordens_servico")
    op.drop_table("ordens_servico")
    op.drop_table("equipamentos")
    op.drop_index("ix_usuarios_cargo_id", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("cargo_permissoes")
    op.drop_table("cargos")
    op.drop_table("sequencias")
