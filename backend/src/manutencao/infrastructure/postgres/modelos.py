"""Modelos SQLAlchemy: o esquema relacional (declaração; a verdade versionada está no Alembic).

Decisões de modelagem (docs/PERSISTENCIA.md):

* **Identificadores** vêm do domínio/aplicação (não há ``SERIAL``): a sequência de cada agregado
  fica em ``sequencias`` e só avança (DLT-10), mesmo depois de uma exclusão.
* **Cargo ↔ permissões** é uma relação (``cargo_permissoes``); ``usuarios.cargo_id`` tem chave
  estrangeira para ``cargos`` (``RESTRICT``).
* **OS** é um agregado: ``ordens_servico`` → ``servicos_os`` (histórico, apenas inclusões) →
  ``pecas_servico``; filhos com ``ON DELETE CASCADE``. Horas, intervenções e peças da OS **não**
  são colunas: derivam dos registros de reparo do histórico (``OrdemServico.restaurar``).
* **Referências da OS** a usuários e equipamento: o contrato da porta diz que a OS guarda
  **cópias** de como eles estavam quando ela foi salva (``*_snapshot``, JSONB); o identificador
  fica numa coluna própria e indexada para filtros e para a regra de participação. **Não há chave
  estrangeira** para ``usuarios``/``equipamentos``: a exclusão de quem tem OS é barrada pela
  aplicação (``usuario_tem_participacao``, ``equipamento_com_os``) e o histórico nunca perde o
  registro de quem agiu.
* **Instantes** são ``timestamptz`` (D-11). Enumerações são texto com ``CHECK`` (portável e
  legível), com os mesmos valores textuais do domínio.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.permissoes import Permissao


def _valores(enum: type[StrEnum]) -> str:
    return ", ".join(f"'{membro.value}'" for membro in enum)


NOMES_DE_RESTRICAO = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa; os nomes de restrição seguem uma convenção estável (Alembic)."""

    metadata = MetaData(naming_convention=NOMES_DE_RESTRICAO)


class SequenciaModelo(Base):
    __tablename__ = "sequencias"
    __table_args__ = (CheckConstraint("ultimo >= 0", name="ultimo_nao_negativo"),)

    entidade: Mapped[str] = mapped_column(String(40), primary_key=True)
    ultimo: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class CargoModelo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    permissoes: Mapped[list["CargoPermissaoModelo"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="CargoPermissaoModelo.permissao"
    )


class CargoPermissaoModelo(Base):
    __tablename__ = "cargo_permissoes"
    __table_args__ = (
        CheckConstraint(f"permissao IN ({_valores(Permissao)})", name="permissao_valida"),
    )

    cargo_id: Mapped[int] = mapped_column(
        ForeignKey("cargos.id", ondelete="CASCADE"), primary_key=True
    )
    permissao: Mapped[str] = mapped_column(String(40), primary_key=True)


class UsuarioModelo(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"papel IN ({_valores(Papel)})", name="papel_valido"),
        CheckConstraint(
            f"disponibilidade IN ({_valores(Disponibilidade)})", name="disponibilidade_valida"
        ),
        # Matrícula AA999999: duas letras maiúsculas e seis dígitos (revisão 0003)
        CheckConstraint("matricula ~ '^[A-Z]{2}[0-9]{6}$'", name="matricula_formato"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    matricula: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cargo_id: Mapped[int] = mapped_column(
        ForeignKey("cargos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, default="")
    escala: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    disponibilidade: Mapped[str] = mapped_column(String(20), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EquipamentoModelo(Base):
    __tablename__ = "equipamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    modelo: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrdemServicoModelo(Base):
    __tablename__ = "ordens_servico"
    __table_args__ = (
        CheckConstraint(f"status IN ({_valores(StatusOS)})", name="status_valido"),
        CheckConstraint(f"criticidade IN ({_valores(Criticidade)})", name="criticidade_valida"),
        Index("ix_ordens_servico_status", "status"),
        Index("ix_ordens_servico_equipamento_id", "equipamento_id"),
        Index("ix_ordens_servico_tecnico_id", "tecnico_id"),
        Index("ix_ordens_servico_aberta_por_id", "aberta_por_id"),
    )

    numero: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    equipamento_id: Mapped[int] = mapped_column(Integer, nullable=False)
    equipamento_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    falha: Mapped[str] = mapped_column(Text, nullable=False)
    criticidade: Mapped[str] = mapped_column(String(20), nullable=False)
    aberta_por_id: Mapped[int] = mapped_column(Integer, nullable=False)
    aberta_por_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    data_abertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    tecnico_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tecnico_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    diagnostico: Mapped[str] = mapped_column(Text, nullable=False, default="")
    causa_raiz: Mapped[str] = mapped_column(Text, nullable=False, default="")
    teste_funcional: Mapped[str] = mapped_column(Text, nullable=False, default="")
    motivo_cancelamento: Mapped[str] = mapped_column(Text, nullable=False, default="")
    data_conclusao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    servicos: Mapped[list["ServicoModelo"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ServicoModelo.numero"
    )


class ServicoModelo(Base):
    """Uma linha do histórico da OS (``Servico`` do domínio)."""

    __tablename__ = "servicos_os"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_valores(TipoServico)})", name="tipo_valido"),
        CheckConstraint("horas >= 0", name="horas_nao_negativas"),
        Index("ix_servicos_os_responsavel_id", "responsavel_id"),
    )

    os_numero: Mapped[int] = mapped_column(
        ForeignKey("ordens_servico.numero", ondelete="CASCADE"), primary_key=True
    )
    numero: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    responsavel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    responsavel_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horas: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    pecas: Mapped[list["PecaModelo"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="PecaModelo.posicao"
    )


class PecaModelo(Base):
    """Peça ou material de um registro de reparo."""

    __tablename__ = "pecas_servico"
    __table_args__ = (
        ForeignKeyConstraint(
            ["os_numero", "servico_numero"],
            ["servicos_os.os_numero", "servicos_os.numero"],
            ondelete="CASCADE",
        ),
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
    )

    os_numero: Mapped[int] = mapped_column(Integer, primary_key=True)
    servico_numero: Mapped[int] = mapped_column(Integer, primary_key=True)
    posicao: Mapped[int] = mapped_column(Integer, primary_key=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    quantidade: Mapped[float] = mapped_column(Double, nullable=False)


class CredencialModelo(Base):
    """Acesso do usuário (D-01): **só o hash** da senha. Quem entra é identificado pela matrícula
    (``usuarios.matricula``). ``login_legado`` guarda o nome de usuário anterior à revisão 0003,
    apenas como registro: não é usado na autenticação e fica ``NULL`` nas contas novas."""

    __tablename__ = "credenciais"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )
    login_legado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SessaoModelo(Base):
    """Sessão do servidor (D-01). ``id_hash`` é o sha256 do token; o token nunca é gravado."""

    __tablename__ = "sessoes"

    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    csrf: Mapped[str] = mapped_column(String(64), nullable=False)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
