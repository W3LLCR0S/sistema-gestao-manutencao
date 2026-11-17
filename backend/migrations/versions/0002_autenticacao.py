"""Autenticação (D-01): credenciais (só hash de senha) e sessões do servidor.

Acrescenta duas tabelas; **não altera** o esquema da revisão 0001. Escrita à mão. As duas tabelas
dependem de ``usuarios`` com ``ON DELETE CASCADE``: excluir um usuário remove o acesso e as sessões.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credenciais",
        sa.Column("usuario_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("login", sa.String(100), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column(
            "atualizada_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name="fk_credenciais_usuario_id_usuarios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("usuario_id", name="pk_credenciais"),
        sa.UniqueConstraint("login", name="uq_credenciais_login"),
    )
    op.create_table(
        "sessoes",
        sa.Column("id_hash", sa.String(64), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("csrf", sa.String(64), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name="fk_sessoes_usuario_id_usuarios",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_hash", name="pk_sessoes"),
    )
    op.create_index("ix_sessoes_usuario_id", "sessoes", ["usuario_id"])
    op.create_index("ix_sessoes_expira_em", "sessoes", ["expira_em"])


def downgrade() -> None:
    op.drop_index("ix_sessoes_expira_em", table_name="sessoes")
    op.drop_index("ix_sessoes_usuario_id", table_name="sessoes")
    op.drop_table("sessoes")
    op.drop_table("credenciais")
