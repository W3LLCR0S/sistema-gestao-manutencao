"""Sequência de identificadores monotônica **persistida** (DLT-10, AUD-05, ADR-0004).

Mesma semântica da sequência em memória, agora sobrevivendo ao reinício: o maior identificador já
emitido fica na tabela ``sequencias`` e nunca recua, nem quando o objeto é excluído. ``registrar``
é um único ``UPDATE ... WHERE ultimo < :id``: o bloqueio da linha serializa emissões concorrentes e
a segunda a chegar com o mesmo identificador é recusada, sem janela de colisão.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from manutencao.application.erros import IdentificadorJaEmitidoError
from manutencao.infrastructure.postgres.modelos import SequenciaModelo


class SequenciaNoBanco:
    """Uma linha de ``sequencias`` (criada pela migração) por agregado."""

    def __init__(self, chave: str, entidade: str) -> None:
        self._chave = chave  # nome estável da linha (ASCII)
        self._entidade = entidade  # nome legível, só para a mensagem de erro

    def proximo(self, sessao: Session) -> int:
        """O identificador que o próximo ``registrar`` aceitaria por padrão (não consome)."""
        ultimo = sessao.scalar(
            select(SequenciaModelo.ultimo).where(SequenciaModelo.entidade == self._chave)
        )
        return (0 if ultimo is None else ultimo) + 1

    def registrar(self, sessao: Session, identificador: int) -> None:
        """Consome ``identificador``, que precisa ser maior que todos os já emitidos."""
        if identificador < 1:
            raise ValueError(f"O identificador de {self._entidade} deve ser positivo.")
        resultado = sessao.execute(
            update(SequenciaModelo)
            .where(SequenciaModelo.entidade == self._chave, SequenciaModelo.ultimo < identificador)
            .values(ultimo=identificador)
        )
        if resultado.rowcount == 0:  # type: ignore[attr-defined]
            raise IdentificadorJaEmitidoError(self._entidade, identificador)
