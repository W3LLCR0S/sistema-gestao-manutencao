"""Conversão das entidades e projeções (domínio/aplicação) nos DTOs de saída (sem regra)."""

from manutencao.api import esquemas as e
from manutencao.application.dto import DisponibilidadeDoTecnico
from manutencao.application.servicos.painel import Painel
from manutencao.domain.cargo import Cargo
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario


def usuario_resumo(u: Usuario) -> e.UsuarioResumo:
    return e.UsuarioResumo(id=u.id, nome=u.nome)


def usuario_saida(u: Usuario) -> e.UsuarioSaida:
    return e.UsuarioSaida(
        id=u.id,
        matricula=u.matricula or "",
        nome=u.nome,
        email=u.email,
        escala=u.escala,
        papel=u.papel,
        ativo=u.ativo,
        disponibilidade=u.disponibilidade,
        cargo=e.CargoResumo(id=u.cargo.id, nome=u.cargo.nome),
        permissoes=[p for p in u.cargo.permissoes.ativas() if u.pode(p)],
    )


def usuario_atual_saida(u: Usuario) -> e.UsuarioAtualSaida:
    return e.UsuarioAtualSaida(**usuario_saida(u).model_dump())


def cargo_saida(c: Cargo) -> e.CargoSaida:
    return e.CargoSaida(id=c.id, nome=c.nome, permissoes=list(c.permissoes.ativas()))


def equipamento_saida(q: Equipamento) -> e.EquipamentoSaida:
    return e.EquipamentoSaida(
        id=q.id, nome=q.nome, modelo=q.modelo, ativo=q.ativo, situacao=q.situacao
    )


def _equipamento_resumo(q: Equipamento) -> e.EquipamentoResumo:
    return e.EquipamentoResumo(id=q.id, nome=q.nome, modelo=q.modelo, ativo=q.ativo)


def _peca(p: PecaMaterial) -> e.PecaSaida:
    return e.PecaSaida(descricao=p.descricao, quantidade=p.quantidade)


def ordem_saida(o: OrdemServico) -> e.OrdemSaida:
    tecnico = o.tecnico_atribuido
    return e.OrdemSaida(
        numero=o.numero,
        status=o.status,
        criticidade=o.criticidade,
        falha=o.falha,
        equipamento=_equipamento_resumo(o.equipamento),
        aberta_por=usuario_resumo(o.aberta_por),
        tecnico=None if tecnico is None else usuario_resumo(tecnico),
        data_abertura=o.data_abertura,
        data_conclusao=o.data_conclusao,
        diagnostico=o.diagnostico,
        causa_raiz=o.causa_raiz,
        teste_funcional=o.teste_funcional,
        motivo_cancelamento=o.motivo_cancelamento,
        horas_trabalhadas=o.horas_trabalhadas,
        intervencoes=list(o.intervencoes_realizadas),
        pecas=[_peca(p) for p in o.pecas_utilizadas],
        encerrada=o.encerrada,
    )


def servico_saida(s: Servico) -> e.ServicoSaida:
    return e.ServicoSaida(
        numero=s.numero,
        tipo=s.tipo,
        descricao=s.descricao,
        responsavel=None if s.responsavel is None else usuario_resumo(s.responsavel),
        data=s.data,
        horas=s.horas,
        pecas=[_peca(p) for p in s.pecas],
    )


def disponibilidade_saida(d: DisponibilidadeDoTecnico) -> e.DisponibilidadeDoTecnicoSaida:
    return e.DisponibilidadeDoTecnicoSaida(
        id=d.id, nome=d.nome, escala=d.escala, disponibilidade=d.disponibilidade, carga=d.carga
    )


def painel_saida(p: Painel) -> e.PainelSaida:
    return e.PainelSaida(
        total=p.total,
        em_aberto=p.em_aberto,
        encerradas=p.encerradas,
        minhas_em_aberto=p.minhas_em_aberto,
        por_status=[e.ContagemPorStatus(status=s, quantidade=n) for s, n in p.por_status],
        por_criticidade_em_aberto=[
            e.ContagemPorCriticidade(criticidade=c, quantidade=n)
            for c, n in p.por_criticidade_em_aberto
        ],
        recentes=[ordem_saida(o) for o in p.recentes],
        tecnicos=None if p.tecnicos is None else [disponibilidade_saida(t) for t in p.tecnicos],
    )
