"""Repositório de ordens de serviço no PostgreSQL (implementa ``OrdemServicoRepository``).

A OS é gravada e lida **como agregado**: linha principal, histórico (``servicos_os``) e peças
(``pecas_servico``) na mesma transação. As consultas por filtro traduzem ``FiltroDeOrdens`` para
SQL; a única regra que ele conhece, "encerrada", vem de ``domain.transicoes.encerrada`` (não é
reescrita aqui). Nenhuma regra de negócio é aplicada ao gravar ou ao ler.
"""

from typing import Any

from sqlalchemy import ColumnElement, delete, exists, func, insert, or_, select, update
from sqlalchemy.orm import Session

from manutencao.application.erros import NaoEncontradoError
from manutencao.application.portas.repositorios import FiltroDeOrdens
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Criticidade, Disponibilidade, Papel, StatusOS, TipoServico
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.permissoes import Permissao, Permissoes
from manutencao.domain.servico import Servico
from manutencao.domain.transicoes import encerrada
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.postgres.banco import Banco
from manutencao.infrastructure.postgres.modelos import (
    OrdemServicoModelo,
    PecaModelo,
    ServicoModelo,
)
from manutencao.infrastructure.postgres.sequencia import SequenciaNoBanco

Snapshot = dict[str, Any]


# ---------------------------------------------------------------- cópias das referências (JSONB)
def _snapshot_usuario(usuario: Usuario) -> Snapshot:
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "cargo": {
            "id": usuario.cargo.id,
            "nome": usuario.cargo.nome,
            "permissoes": [p.value for p in usuario.cargo.permissoes.ativas()],
        },
        "email": usuario.email,
        "escala": usuario.escala,
        "disponibilidade": usuario.disponibilidade.value,
        "papel": usuario.papel.value,
        "ativo": usuario.ativo,
    }


def _usuario(snapshot: Snapshot) -> Usuario:
    cargo = snapshot["cargo"]
    return Usuario(
        snapshot["id"],
        snapshot["nome"],
        Cargo(cargo["id"], cargo["nome"], Permissoes(Permissao(p) for p in cargo["permissoes"])),
        snapshot["email"],
        snapshot["escala"],
        Disponibilidade(snapshot["disponibilidade"]),
        papel=Papel(snapshot["papel"]),
        ativo=snapshot["ativo"],
    )


def _snapshot_equipamento(equipamento: Equipamento) -> Snapshot:
    return {
        "id": equipamento.id,
        "nome": equipamento.nome,
        "modelo": equipamento.modelo,
        "ativo": equipamento.ativo,
    }


def _equipamento(snapshot: Snapshot) -> Equipamento:
    return Equipamento(snapshot["id"], snapshot["nome"], snapshot["modelo"], snapshot["ativo"])


# ---------------------------------------------------------------- linhas <-> agregado
def _linha_da_os(ordem: OrdemServico) -> dict[str, Any]:
    tecnico = ordem.tecnico_atribuido
    return {
        "equipamento_id": ordem.equipamento.id,
        "equipamento_snapshot": _snapshot_equipamento(ordem.equipamento),
        "falha": ordem.falha,
        "criticidade": ordem.criticidade.value,
        "aberta_por_id": ordem.aberta_por.id,
        "aberta_por_snapshot": _snapshot_usuario(ordem.aberta_por),
        "data_abertura": ordem.data_abertura,
        "status": ordem.status.value,
        "tecnico_id": None if tecnico is None else tecnico.id,
        "tecnico_snapshot": None if tecnico is None else _snapshot_usuario(tecnico),
        "diagnostico": ordem.diagnostico,
        "causa_raiz": ordem.causa_raiz,
        "teste_funcional": ordem.teste_funcional,
        "motivo_cancelamento": ordem.motivo_cancelamento,
        "data_conclusao": ordem.data_conclusao,
    }


def _gravar_historico(sessao: Session, ordem: OrdemServico) -> None:
    servicos: list[dict[str, Any]] = []
    pecas: list[dict[str, Any]] = []
    for servico in ordem.servicos:
        responsavel = servico.responsavel
        servicos.append(
            {
                "os_numero": ordem.numero,
                "numero": servico.numero,
                "tipo": servico.tipo.value,
                "descricao": servico.descricao,
                "responsavel_id": None if responsavel is None else responsavel.id,
                "responsavel_snapshot": (
                    None if responsavel is None else _snapshot_usuario(responsavel)
                ),
                "data": servico.data,
                "horas": servico.horas,
            }
        )
        pecas.extend(
            {
                "os_numero": ordem.numero,
                "servico_numero": servico.numero,
                "posicao": posicao,
                "descricao": peca.descricao,
                "quantidade": peca.quantidade,
            }
            for posicao, peca in enumerate(servico.pecas, start=1)
        )
    if servicos:
        sessao.execute(insert(ServicoModelo), servicos)
    if pecas:
        sessao.execute(insert(PecaModelo), pecas)


def _servico(modelo: ServicoModelo) -> Servico:
    responsavel = modelo.responsavel_snapshot
    return Servico(
        modelo.numero,
        TipoServico(modelo.tipo),
        modelo.descricao,
        None if responsavel is None else _usuario(responsavel),
        modelo.data,
        modelo.horas,
        tuple(PecaMaterial(p.descricao, p.quantidade) for p in modelo.pecas),
    )


def _ordem(modelo: OrdemServicoModelo) -> OrdemServico:
    tecnico = modelo.tecnico_snapshot
    return OrdemServico.restaurar(
        numero=modelo.numero,
        equipamento=_equipamento(modelo.equipamento_snapshot),
        falha=modelo.falha,
        criticidade=Criticidade(modelo.criticidade),
        aberta_por=_usuario(modelo.aberta_por_snapshot),
        data_abertura=modelo.data_abertura,
        status=StatusOS(modelo.status),
        tecnico_atribuido=None if tecnico is None else _usuario(tecnico),
        diagnostico=modelo.diagnostico,
        causa_raiz=modelo.causa_raiz,
        teste_funcional=modelo.teste_funcional,
        motivo_cancelamento=modelo.motivo_cancelamento,
        data_conclusao=modelo.data_conclusao,
        servicos=[_servico(s) for s in modelo.servicos],
    )


def _condicoes(filtro: FiltroDeOrdens | None) -> list[ColumnElement[bool]]:
    """Tradução SQL de ``FiltroDeOrdens`` (os informados se combinam com E)."""
    if filtro is None:
        return []
    condicoes: list[ColumnElement[bool]] = []
    if filtro.status is not None:
        condicoes.append(OrdemServicoModelo.status == filtro.status.value)
    if filtro.criticidade is not None:
        condicoes.append(OrdemServicoModelo.criticidade == filtro.criticidade.value)
    if filtro.equipamento_id is not None:
        condicoes.append(OrdemServicoModelo.equipamento_id == filtro.equipamento_id)
    if filtro.tecnico_id is not None:
        condicoes.append(OrdemServicoModelo.tecnico_id == filtro.tecnico_id)
    if filtro.encerrada is not None:
        em_estado_final = OrdemServicoModelo.status.in_(
            [status.value for status in StatusOS if encerrada(status)]
        )
        condicoes.append(em_estado_final if filtro.encerrada else ~em_estado_final)
    return condicoes


class OrdensNoBanco:
    """Ordens de serviço. Cada chamada é uma transação (ou participa da externa)."""

    def __init__(self, banco: Banco) -> None:
        self._banco = banco
        self._sequencia = SequenciaNoBanco("ordem_servico", "Ordem de serviço")

    def proximo_numero(self) -> int:
        with self._banco.transacao() as sessao:
            return self._sequencia.proximo(sessao)

    def adicionar(self, ordem: OrdemServico) -> None:
        with self._banco.transacao() as sessao:
            self._sequencia.registrar(sessao, ordem.numero)
            sessao.execute(
                insert(OrdemServicoModelo).values(numero=ordem.numero, **_linha_da_os(ordem))
            )
            _gravar_historico(sessao, ordem)

    def obter(self, numero: int) -> OrdemServico | None:
        with self._banco.transacao() as sessao:
            modelo = sessao.get(OrdemServicoModelo, numero, populate_existing=True)
            return None if modelo is None else _ordem(modelo)

    def listar(self, filtro: FiltroDeOrdens | None = None) -> tuple[OrdemServico, ...]:
        with self._banco.transacao() as sessao:
            modelos = sessao.scalars(
                select(OrdemServicoModelo)
                .where(*_condicoes(filtro))
                .order_by(OrdemServicoModelo.numero)
                .execution_options(populate_existing=True)
            ).all()
            return tuple(_ordem(m) for m in modelos)

    def contar(self, filtro: FiltroDeOrdens | None = None) -> int:
        with self._banco.transacao() as sessao:
            total = sessao.scalar(
                select(func.count()).select_from(OrdemServicoModelo).where(*_condicoes(filtro))
            )
            return int(total or 0)

    def salvar(self, ordem: OrdemServico) -> None:
        with self._banco.transacao() as sessao:
            atualizadas = sessao.execute(
                update(OrdemServicoModelo)
                .where(OrdemServicoModelo.numero == ordem.numero)
                .values(**_linha_da_os(ordem))
            )
            if atualizadas.rowcount == 0:  # type: ignore[attr-defined]
                raise NaoEncontradoError("Ordem de serviço", ordem.numero)
            # O histórico é reescrito por inteiro na mesma transação: a entidade só o amplia, então
            # o resultado é o mesmo de um acréscimo, sem depender de comparar o que já existia.
            sessao.execute(delete(ServicoModelo).where(ServicoModelo.os_numero == ordem.numero))
            _gravar_historico(sessao, ordem)
            sessao.expire_all()

    def usuario_tem_participacao(self, usuario_id: int) -> bool:
        with self._banco.transacao() as sessao:
            como_tecnico_ou_autor = exists().where(
                or_(
                    OrdemServicoModelo.tecnico_id == usuario_id,
                    OrdemServicoModelo.aberta_por_id == usuario_id,
                )
            )
            como_responsavel = exists().where(ServicoModelo.responsavel_id == usuario_id)
            return bool(sessao.scalar(select(como_tecnico_ou_autor | como_responsavel)))
