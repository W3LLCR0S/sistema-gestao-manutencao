"""Dados **fictícios** de demonstração (Fase 03), independentes do legado.

Nada aqui lê ``dados/`` nem converte dados reais (D-08): os nomes, e-mails e equipamentos são
inventados. Tudo passa pelos **serviços** (portanto pelas regras reais): usuários, equipamentos e
algumas OS em estados diferentes, para a interface e a API terem o que mostrar. A semente se
recusa a rodar em um banco que já tem dados.

Contas: ``1 Ana Souza`` (gestora), ``2 Bruno Lima`` e ``3 Carla Mendes`` (técnicos). A autenticação
(D-01) ainda não existe; os identificadores são os atores dos casos de uso.
"""

from dataclasses import dataclass

from manutencao.application.dto import PecaInformada
from manutencao.composicao.container import Container
from manutencao.composicao.fabrica import semear_dados_de_exemplo
from manutencao.domain.enums import Criticidade, StatusOS

ANA, BRUNO, CARLA = 1, 2, 3
TORNO, COMPRESSOR, EMPILHADEIRA = 1, 2, 3


class BancoNaoVazioError(Exception):
    """A semente só roda em um banco sem cargos, usuários, equipamentos nem OS."""


@dataclass(frozen=True)
class ResumoDaDemonstracao:
    cargos: int
    usuarios: int
    equipamentos: int
    ordens: int


def _banco_vazio(c: Container) -> bool:
    return not (
        c.cargos.listar() or c.usuarios.listar() or c.equipamentos.listar() or c.ordens.listar()
    )


def semear_demonstracao(c: Container) -> ResumoDaDemonstracao:
    """Cadastra a base fictícia e cinco OS: aberta, atribuída, em execução, concluída, cancelada."""
    if not _banco_vazio(c):
        raise BancoNaoVazioError(
            "O banco já contém dados; a demonstração só semeia um banco vazio."
        )
    semear_dados_de_exemplo(c.equipamentos, c.cargos, c.usuarios)
    os_ = c.servico_ordens

    os_.abrir(ANA, TORNO, "Vibração excessiva no eixo principal durante o corte.", Criticidade.ALTA)

    atribuida = os_.abrir(BRUNO, COMPRESSOR, "Queda de pressão após 2 h de uso.", Criticidade.MEDIA)
    os_.atribuir(ANA, atribuida.numero, BRUNO)

    em_execucao = os_.abrir(CARLA, EMPILHADEIRA, "Bateria não segura carga.", Criticidade.CRITICA)
    os_.atribuir(ANA, em_execucao.numero, CARLA)
    os_.registrar_diagnostico(
        CARLA, em_execucao.numero, "Células da bateria degradadas", "Ciclos de carga excessivos"
    )
    os_.apontar_reparo(
        CARLA,
        em_execucao.numero,
        2.5,
        "Substituição do módulo de células",
        [PecaInformada("Módulo de células 48 V", 1)],
    )

    concluida = os_.abrir(ANA, TORNO, "Ruído no rolamento do fuso.", Criticidade.BAIXA)
    os_.atribuir(ANA, concluida.numero, BRUNO)
    os_.registrar_diagnostico(
        BRUNO, concluida.numero, "Rolamento desgastado", "Falta de lubrificação"
    )
    os_.apontar_reparo(
        BRUNO,
        concluida.numero,
        1.5,
        "Troca do rolamento e lubrificação",
        [PecaInformada("Rolamento 6205", 2), PecaInformada("Graxa (kg)", 0.2)],
    )
    os_.alterar_status(BRUNO, concluida.numero, StatusOS.REPARO_FINALIZADO)
    os_.concluir_tecnicamente(BRUNO, concluida.numero, "Operação sem ruído por 30 min", True)
    os_.aprovar(ANA, concluida.numero)

    cancelada = os_.abrir(BRUNO, COMPRESSOR, "Chamado aberto em duplicidade.", Criticidade.BAIXA)
    os_.cancelar(ANA, cancelada.numero, "Duplicado da OS 2")

    return ResumoDaDemonstracao(
        cargos=len(c.cargos.listar()),
        usuarios=len(c.usuarios.listar()),
        equipamentos=len(c.equipamentos.listar()),
        ordens=c.ordens.contar(),
    )
