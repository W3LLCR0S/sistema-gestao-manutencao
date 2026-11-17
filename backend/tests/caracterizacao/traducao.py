"""Tradução das entidades do domínio para os snapshots e recusas da fachada de caracterização.

Compartilhada pelos adaptadores que falam com o domínio (``adaptador_dominio`` e
``adaptador_servicos``): ambos precisam mostrar o mesmo formato que o adaptador do legado. Só
conhece o **domínio** e a fachada; nada de aplicação nem de infraestrutura.

* **Datas.** O domínio guarda instantes UTC; o snapshot compatível com o legado mostra o instante
  normalizado em UTC no formato ``dd/mm/aaaa hh:mm``. Não há conversão para
  ``America/Sao_Paulo`` (apresentação, Fase 04).
* **Recusas.** São classificadas pelo **código** do erro de domínio, não pelo texto: a categoria é a
  mesma do adaptador do legado, que a deriva da mensagem.
"""

from datetime import UTC, datetime

from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.erros import CodigoErro
from manutencao.domain.ordem_servico import OrdemServico
from manutencao.domain.peca_material import PecaMaterial
from manutencao.domain.servico import Servico
from manutencao.domain.usuario import Usuario
from tests.caracterizacao.fachada import (
    CargoSnap,
    EquipamentoSnap,
    OsSnap,
    PecaSnap,
    Recusa,
    ServicoSnap,
    UsuarioSnap,
)

RECUSA_POR_CODIGO: dict[CodigoErro, Recusa] = {
    CodigoErro.SEM_PERMISSAO: Recusa.SEM_PERMISSAO,
    CodigoErro.NAO_RESPONSAVEL: Recusa.NAO_RESPONSAVEL,
    CodigoErro.ESTADO_INVALIDO: Recusa.ESTADO_INVALIDO,
    CodigoErro.OS_ENCERRADA: Recusa.OS_ENCERRADA,
    CodigoErro.JA_ATRIBUIDA: Recusa.JA_ATRIBUIDA,
    CodigoErro.JA_NESSE_STATUS: Recusa.JA_NESSE_STATUS,
    CodigoErro.EQUIPAMENTO_INATIVO: Recusa.EQUIPAMENTO_INATIVO,
    CodigoErro.NAO_E_TECNICO: Recusa.NAO_E_TECNICO,
    CodigoErro.STATUS_NAO_PERMITIDO: Recusa.STATUS_NAO_PERMITIDO,
    CodigoErro.SEM_INTERVENCAO: Recusa.SEM_INTERVENCAO,
    CodigoErro.SEM_DIAGNOSTICO: Recusa.SEM_DIAGNOSTICO,
    CodigoErro.HORAS_NEGATIVAS: Recusa.HORAS_NEGATIVAS,
    CodigoErro.QUANTIDADE_INVALIDA: Recusa.QUANTIDADE_INVALIDA,
    # Operação E: comportamentos novos, sem equivalente no legado.
    CodigoErro.TECNICO_AUSENTE: Recusa.TECNICO_AUSENTE,
    CodigoErro.SEM_VINCULO_COM_A_OS: Recusa.SEM_VINCULO_COM_A_OS,
    CodigoErro.CAMPO_OBRIGATORIO: Recusa.CAMPO_OBRIGATORIO,
    CodigoErro.HORAS_NAO_POSITIVAS: Recusa.HORAS_NAO_POSITIVAS,
    CodigoErro.USUARIO_INATIVO: Recusa.USUARIO_INATIVO,
    CodigoErro.DISPONIBILIDADE_MANUAL_INVALIDA: Recusa.DISPONIBILIDADE_MANUAL_INVALIDA,
    # Sem equivalente no legado: se aparecer num cenário, o teste deve falhar.
    CodigoErro.PERMISSAO_INVALIDA: Recusa.DESCONHECIDA,
    CodigoErro.INSTANTE_INVALIDO: Recusa.DESCONHECIDA,
}


def texto_legado(instante: datetime) -> str:
    """Instante UTC no formato de texto do legado (``dd/mm/aaaa hh:mm``, sem fuso)."""
    return instante.astimezone(UTC).strftime("%d/%m/%Y %H:%M")


def snap_peca(p: PecaMaterial) -> PecaSnap:
    return PecaSnap(p.descricao, float(p.quantidade))


def snap_servico(s: Servico) -> ServicoSnap:
    return ServicoSnap(
        s.numero,
        s.tipo.value,
        s.descricao,
        None if s.responsavel is None else s.responsavel.id,
        texto_legado(s.data),
        float(s.horas),
        tuple(snap_peca(p) for p in s.pecas),
    )


def snap_os(o: OrdemServico) -> OsSnap:
    return OsSnap(
        numero=o.numero,
        status=o.status.value,
        equipamento_id=o.equipamento.id,
        falha=o.falha,
        criticidade=o.criticidade.value,
        aberta_por_id=o.aberta_por.id,
        tecnico_id=None if o.tecnico_atribuido is None else o.tecnico_atribuido.id,
        diagnostico=o.diagnostico,
        causa_raiz=o.causa_raiz,
        horas_trabalhadas=float(o.horas_trabalhadas),
        intervencoes=o.intervencoes_realizadas,
        pecas=tuple(snap_peca(p) for p in o.pecas_utilizadas),
        data_abertura=texto_legado(o.data_abertura),
        data_conclusao=None if o.data_conclusao is None else texto_legado(o.data_conclusao),
        teste_funcional=o.teste_funcional,
        motivo_cancelamento=o.motivo_cancelamento,
        historico=tuple(snap_servico(s) for s in o.servicos),
    )


def snap_usuario(
    u: Usuario, carga: int, disponibilidade: Disponibilidade | None = None
) -> UsuarioSnap:
    """``disponibilidade`` é a derivada das OS (D-05); sem ela, o valor guardado no usuário."""
    efetiva = u.disponibilidade if disponibilidade is None else disponibilidade
    return UsuarioSnap(
        id=u.id,
        nome=u.nome,
        cargo_id=u.cargo.id,
        cargo=u.cargo.nome,
        email=u.email,
        escala=u.escala,
        disponibilidade=efetiva.value,
        carga=carga,
    )


def snap_equipamento(e: Equipamento) -> EquipamentoSnap:
    return EquipamentoSnap(e.id, e.nome, e.modelo, e.ativo)


def snap_cargo(c: Cargo) -> CargoSnap:
    return CargoSnap(c.id, c.nome, tuple(p.value for p in c.permissoes.ativas()))
