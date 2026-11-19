"""Fábrica da raiz de composição: escolhe as implementações concretas.

É o **único** lugar (com os testes e a administração do banco) que importa a infraestrutura. Há
duas composições, sem que os serviços saibam qual está em uso: **em memória** (testes; D-10: sem
JSON) e **PostgreSQL** (Fase 03). Cada chamada devolve um contêiner novo, sem estado compartilhado.
"""

from manutencao.application.portas.relogio import Relogio
from manutencao.application.portas.repositorios import (
    CargoRepository,
    EquipamentoRepository,
    UsuarioRepository,
)
from manutencao.composicao.container import Container, montar
from manutencao.domain.cargo import Cargo
from manutencao.domain.enums import Papel
from manutencao.domain.equipamento import Equipamento
from manutencao.domain.permissoes import Permissoes
from manutencao.domain.usuario import Usuario
from manutencao.infrastructure.memoria import (
    CargosEmMemoria,
    EquipamentosEmMemoria,
    OrdensEmMemoria,
    UsuariosEmMemoria,
)
from manutencao.infrastructure.postgres import (
    Banco,
    CargosNoBanco,
    EquipamentosNoBanco,
    OrdensNoBanco,
    UsuariosNoBanco,
)
from manutencao.infrastructure.relogio import RelogioDeSistema


def semear_dados_de_exemplo(
    equipamentos: EquipamentoRepository,
    cargos: CargoRepository,
    usuarios: UsuarioRepository,
) -> None:
    """A base inicial do legado (``_popular_exemplo``), cadastrada pelas portas.

    Cargos fixos 1 Gestor e 2 Técnico; usuários 1 Ana (gestora, matrícula KM482731), 2 Bruno
    (RT095624) e 3 Carla (VX716309) (técnicos); equipamentos 1 Torno CNC, 2 Compressor de Ar e
    3 Empilhadeira Elétrica. Os identificadores saem da sequência de cada repositório, que depois
    segue em 4 (ou 3, no caso dos cargos).
    """
    gestor = Cargo(cargos.proximo_id(), "Gestor", Permissoes.padrao_gestor())
    cargos.adicionar(gestor)
    tecnico = Cargo(cargos.proximo_id(), "Técnico", Permissoes.padrao_tecnico())
    cargos.adicionar(tecnico)
    for nome, cargo, papel, email, escala, matricula in (
        ("Ana Souza", gestor, Papel.GESTOR, "ana@empresa.com", "Seg-Sex 08h-17h", "KM482731"),
        ("Bruno Lima", tecnico, Papel.TECNICO, "bruno@empresa.com", "Seg-Sex 07h-16h", "RT095624"),
        (
            "Carla Mendes",
            tecnico,
            Papel.TECNICO,
            "carla@empresa.com",
            "Seg-Sex 13h-22h",
            "VX716309",
        ),
    ):
        usuarios.adicionar(
            Usuario(
                usuarios.proximo_id(),
                nome,
                cargo,
                email,
                escala,
                papel=papel,
                matricula=matricula,
            )
        )
    for nome, modelo in (
        ("Torno CNC", "GL 240"),
        ("Compressor de Ar", "CSW 40"),
        ("Empilhadeira Elétrica", "PT 1650"),
    ):
        equipamentos.adicionar(Equipamento(equipamentos.proximo_id(), nome, modelo))


def criar_container_em_memoria(
    *, relogio: Relogio | None = None, com_dados_de_exemplo: bool = False
) -> Container:
    """Um contêiner novo com repositórios em memória.

    ``relogio`` padrão é o relógio de sistema (UTC); testes passam um relógio fixo.
    ``com_dados_de_exemplo`` carrega a base inicial do legado (vazio por padrão).
    """
    equipamentos = EquipamentosEmMemoria()
    cargos = CargosEmMemoria()
    usuarios = UsuariosEmMemoria(cargos)
    ordens = OrdensEmMemoria()
    if com_dados_de_exemplo:
        semear_dados_de_exemplo(equipamentos, cargos, usuarios)
    return montar(
        relogio=relogio if relogio is not None else RelogioDeSistema(),
        equipamentos=equipamentos,
        cargos=cargos,
        usuarios=usuarios,
        ordens=ordens,
    )


def criar_container_postgres(banco: Banco, *, relogio: Relogio | None = None) -> Container:
    """Um contêiner cujos repositórios gravam no PostgreSQL de ``banco`` (esquema já migrado).

    Os dados sobrevivem ao reinício: um contêiner novo sobre o mesmo banco vê tudo o que o anterior
    gravou, inclusive a sequência de identificadores. Nenhum dado é criado aqui (ver
    ``demonstracao.semear_demonstracao``).
    """
    cargos = CargosNoBanco(banco)
    return montar(
        relogio=relogio if relogio is not None else RelogioDeSistema(),
        equipamentos=EquipamentosNoBanco(banco),
        cargos=cargos,
        usuarios=UsuariosNoBanco(banco, cargos),
        ordens=OrdensNoBanco(banco),
    )
