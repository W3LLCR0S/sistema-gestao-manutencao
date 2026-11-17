"""Hash de senhas com Argon2id (``argon2-cffi``), implementação de ``HasherDeSenha``.

Os parâmetros padrão são os do perfil recomendado pela biblioteca (RFC 9106, baixa memória). Os
testes usam parâmetros mínimos só para acelerar a suíte; nunca em execução real.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class HasherArgon2:
    def __init__(
        self,
        *,
        time_cost: int | None = None,
        memory_cost: int | None = None,
        parallelism: int | None = None,
    ) -> None:
        padrao = PasswordHasher()
        self._hasher = PasswordHasher(
            time_cost=padrao.time_cost if time_cost is None else time_cost,
            memory_cost=padrao.memory_cost if memory_cost is None else memory_cost,
            parallelism=padrao.parallelism if parallelism is None else parallelism,
        )

    def gerar(self, senha: str) -> str:
        return self._hasher.hash(senha)

    def verificar(self, senha_hash: str, senha: str) -> bool:
        try:
            return self._hasher.verify(senha_hash, senha)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def precisa_renovar(self, senha_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(senha_hash)
        except InvalidHashError:
            return False
