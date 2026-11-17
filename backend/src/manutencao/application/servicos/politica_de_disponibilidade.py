"""Política única da disponibilidade **manual** (REG-E-06, DLT-15).

Há duas portas de entrada para ajustar a disponibilidade manual de um usuário
(``ServicoDeUsuarios.definir_disponibilidade`` e
``ServicoDeDisponibilidade.alterar_disponibilidade``). Ambas chamam esta função, para que a
autorização e os valores aceitos não existam em duas implementações independentes:

* o usuário altera a **própria** disponibilidade, sem exigir permissão (como no legado);
* quem tem ``gerir_usuarios`` altera a de **outro** usuário; quem não tem é recusado por
  autorização, antes de procurar o alvo (DLT-16) e sem mutação;
* o valor manual é só ``Disponível`` ou ``Ausente``: ``Em atendimento`` é derivado das OS e nunca é
  gravado (recusa de domínio, sem mutação).

Trata de **quem** pode alterar e **o que** pode ser gravado. A disponibilidade efetiva continua
sendo a derivada das OS, com a ausência manual prevalecendo (D-05).
"""

from manutencao.application.portas.repositorios import UsuarioRepository
from manutencao.application.servicos.comum import carregar_ator, exigir_encontrado
from manutencao.domain.enums import Disponibilidade
from manutencao.domain.permissoes import Permissao
from manutencao.domain.usuario import Usuario


def alterar_disponibilidade_manual(
    usuarios: UsuarioRepository, ator_id: int, usuario_id: int, valor: Disponibilidade
) -> Usuario:
    """Grava o valor manual de ``usuario_id`` se ``ator_id`` puder e o valor for aceito."""
    ator = carregar_ator(usuarios, ator_id)
    if usuario_id == ator.id:
        alvo = ator
    else:
        ator.exigir(Permissao.GERIR_USUARIOS)
        alvo = exigir_encontrado("Usuário", usuario_id, usuarios.obter(usuario_id))
    alvo.definir_disponibilidade_manual(valor)  # recusa o valor antes de qualquer gravação
    usuarios.salvar(alvo)
    return alvo
