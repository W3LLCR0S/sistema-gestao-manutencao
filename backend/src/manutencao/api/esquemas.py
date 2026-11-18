"""DTOs da API (Pydantic): o contrato HTTP, separado das entidades do domínio.

* **Entrada:** ``extra="forbid"`` (um campo desconhecido, como ``ator_id``, é recusado: 422),
  limites
  de tamanho e tipos fortes. Senhas não são normalizadas nem cortadas. Regras de negócio (texto
  obrigatório, horas positivas...) continuam no domínio: aqui só a forma.
* **Saída:** campos explícitos. Nunca há hash de senha, token de sessão nem dado interno. Instantes
  saem em ISO 8601 com fuso (UTC, D-11); a conversão para America/Sao_Paulo é da interface.
"""

from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from manutencao.domain.enums import (
    Criticidade,
    Disponibilidade,
    Papel,
    StatusOS,
    TipoServico,
)
from manutencao.domain.permissoes import Permissao

T = TypeVar("T")

# Texto aparado nas pontas; o tamanho mínimo/obrigatoriedade é do domínio.
Texto200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Texto254 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)]
Texto100 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
TextoLongo = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Senha = Annotated[str, StringConstraints(max_length=128)]  # sem strip: a senha é como foi digitada


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Saida(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------------------------- erros e paginação
class DetalheDeCampo(Saida):
    campo: str
    mensagem: str


class ErroSaida(Saida):
    """Corpo de toda resposta de erro (``detalhes`` só em 422 de validação de forma)."""

    codigo: str
    mensagem: str
    detalhes: list[DetalheDeCampo] | None = None


class Pagina(Saida, Generic[T]):
    itens: list[T]
    total: int
    limite: int
    deslocamento: int


# ------------------------------------------------------------------------------------ autenticação
class LoginEntrada(Entrada):
    # Sem validar o formato aqui: uma matrícula malformada recebe a mesma recusa (401) que uma
    # desconhecida, sem pistas de quais valores existem.
    matricula: Annotated[str, Field(max_length=64)]
    senha: Senha


class SenhaAlterarEntrada(Entrada):
    senha_atual: Senha
    nova_senha: Senha


class CredencialEntrada(Entrada):
    senha: Senha


class CargoResumo(Saida):
    id: int
    nome: str


class UsuarioSaida(Saida):
    id: int
    matricula: str  # AA999999: gerada pelo sistema, imutável
    nome: str
    email: str
    escala: str
    papel: Papel
    ativo: bool
    disponibilidade: Disponibilidade  # o valor **manual**; o derivado vem de /disponibilidade
    cargo: CargoResumo
    permissoes: list[Permissao]  # efetivas: vazio para usuário inativo


class UsuarioAtualSaida(UsuarioSaida):
    """O usuário autenticado (a matrícula já vem em ``UsuarioSaida``)."""


class SessaoSaida(Saida):
    usuario: UsuarioAtualSaida
    csrf_token: str
    expira_em: datetime


class VerificacaoDeSessaoSaida(Saida):
    autenticado: bool
    usuario_id: int
    expira_em: datetime


class PermissaoVerificadaSaida(Saida):
    permissao: Permissao
    concedida: bool


class PermissaoSaida(Saida):
    nome: Permissao
    descricao: str


# ---------------------------------------------------------------------------------------- usuários
class UsuarioCriarEntrada(Entrada):
    nome: Texto200
    cargo_id: int
    papel: Papel
    email: Texto254 = ""
    escala: Texto100 = ""
    senha: Senha | None = None  # opcional; a matrícula NUNCA é informada: é gerada


class UsuarioAtualizarEntrada(Entrada):
    nome: Texto200 | None = None
    email: Texto254 | None = None
    escala: Texto100 | None = None


class CargoAlterarEntrada(Entrada):
    cargo_id: int


class PapelAlterarEntrada(Entrada):
    papel: Papel


class DisponibilidadeAlterarEntrada(Entrada):
    disponibilidade: Disponibilidade


class CargoSaida(Saida):
    id: int
    nome: str
    permissoes: list[Permissao]


class PermissoesDefinirEntrada(Entrada):
    permissoes: list[Permissao] = Field(max_length=len(Permissao))


class DisponibilidadeDoTecnicoSaida(Saida):
    id: int
    nome: str
    escala: str
    disponibilidade: Disponibilidade  # derivada das OS (D-05)
    carga: int


# ------------------------------------------------------------------------------------ equipamentos
class EquipamentoEntrada(Entrada):
    nome: Texto200
    modelo: Texto200


class EquipamentoSaida(Saida):
    id: int
    nome: str
    modelo: str
    ativo: bool
    situacao: str


# ------------------------------------------------------------------------------ ordens de serviço
class UsuarioResumo(Saida):
    id: int
    nome: str


class EquipamentoResumo(Saida):
    id: int
    nome: str
    modelo: str
    ativo: bool


class PecaSaida(Saida):
    descricao: str
    quantidade: float


class OrdemSaida(Saida):
    numero: int
    status: StatusOS
    criticidade: Criticidade
    falha: str
    equipamento: EquipamentoResumo
    aberta_por: UsuarioResumo
    tecnico: UsuarioResumo | None
    data_abertura: datetime
    data_conclusao: datetime | None
    diagnostico: str
    causa_raiz: str
    teste_funcional: str
    motivo_cancelamento: str
    horas_trabalhadas: float
    intervencoes: list[str]
    pecas: list[PecaSaida]
    encerrada: bool


class ServicoSaida(Saida):
    numero: int
    tipo: TipoServico
    descricao: str
    responsavel: UsuarioResumo | None
    data: datetime
    horas: float
    pecas: list[PecaSaida]


class OrdemAbrirEntrada(Entrada):
    equipamento_id: int
    falha: TextoLongo
    criticidade: Criticidade


class DiagnosticoEntrada(Entrada):
    parecer: TextoLongo
    causa_raiz: TextoLongo


class AtribuicaoEntrada(Entrada):
    tecnico_id: int
    confirmar_ausente: bool = False


class PecaEntrada(Entrada):
    descricao: Texto200
    quantidade: float = Field(allow_inf_nan=False)


class ReparoEntrada(Entrada):
    horas: float = Field(allow_inf_nan=False)
    intervencao: TextoLongo
    pecas: list[PecaEntrada] = Field(default_factory=list, max_length=50)


class StatusEntrada(Entrada):
    status: StatusOS


class ConclusaoTecnicaEntrada(Entrada):
    teste: TextoLongo
    passou: bool


class MotivoEntrada(Entrada):
    motivo: TextoLongo


class ApontamentoEntrada(Entrada):
    texto: TextoLongo


class ConclusaoTecnicaSaida(Saida):
    submetida_a_aprovacao: bool
    ordem: OrdemSaida


class AtribuicaoSaida(Saida):
    ordem: OrdemSaida
    tecnico_anterior: UsuarioResumo | None


# ------------------------------------------------------------------------------------------ painel
class ContagemPorStatus(Saida):
    status: StatusOS
    quantidade: int


class ContagemPorCriticidade(Saida):
    criticidade: Criticidade
    quantidade: int


class PainelSaida(Saida):
    total: int
    em_aberto: int
    encerradas: int
    minhas_em_aberto: int
    por_status: list[ContagemPorStatus]
    por_criticidade_em_aberto: list[ContagemPorCriticidade]
    recentes: list[OrdemSaida]
    tecnicos: list[DisponibilidadeDoTecnicoSaida] | None


class SaudeSaida(Saida):
    status: str
    banco: str
