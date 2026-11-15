"""Tela de Usuários, Cargos e Permissões (gestor)."""

from models import Usuario, Cargo, Permissoes, Disponibilidade, RegraNegocioError
from ui.entrada import titulo, ler, ler_int, escolher, confirmar
from ui.tela_base import TelaBase


class TelaUsuarios(TelaBase):

    # ============================ usuários ============================
    def listar_usuarios(self):
        print(f"\n  {'ID':<4}{'Nome':<22}{'Cargo':<12}{'E-mail':<24}{'Disponibilidade'}")
        for u in self.repo.usuarios:
            print(f"  {u.id:<4}{u.nome[:21]:<22}{u.cargo.nome[:11]:<12}{u.email[:23]:<24}{u.disponibilidade}")

    def gerenciar_usuarios(self):
        self.usuario.exigir("gerir_usuarios")
        while True:
            titulo("GERENCIAR USUÁRIOS")
            self.listar_usuarios()
            print("\n  1. Cadastrar  2. Editar  3. Excluir  0. Voltar")
            op = ler_int("Opção")
            if op == 0:
                return
            try:
                if op == 1:
                    self._cadastrar_usuario()
                elif op in (2, 3):
                    u = self.repo.buscar_usuario(ler_int("ID do usuário"))
                    if not u:
                        print("  ! Não encontrado.")
                    elif op == 2:
                        self._editar_usuario(u)
                    elif confirmar(f"Excluir '{u.nome}'?"):
                        self.repo.remover_usuario(u, self.usuario)
                        print("  ✓ Usuário excluído.")
            except RegraNegocioError as erro:
                print(f"  ! {erro}")
            self.repo.salvar()

    def _cadastrar_usuario(self):
        print("\n  Novo usuário")
        nome = ler("Nome")
        email = ler("E-mail", obrigatorio=False)
        escala = ler("Escala (ex.: Seg-Sex 08h-17h)", obrigatorio=False)
        cargo = escolher("Cargo", self.repo.cargos)
        u = Usuario(self.repo.proximo_id_usuario(), nome, cargo, email, escala)
        self.repo.adicionar_usuario(u)
        print(f"  ✓ Usuário #{u.id} cadastrado como {cargo}.")

    def _editar_usuario(self, u: Usuario):
        u.nome = ler("Nome", padrao=u.nome)
        u.email = ler("E-mail", padrao=u.email)
        u.escala = ler("Escala", padrao=u.escala)
        print(f"  Cargo atual: {u.cargo}")
        novo = escolher("Cargo", self.repo.cargos, permitir_vazio=True)
        if novo:
            if u is self.usuario and not novo.permissoes.gerir_usuarios:
                raise RegraNegocioError("Você não pode remover o próprio acesso de gestão.")
            u.cargo = novo
        print(f"  Disponibilidade atual: {u.disponibilidade}")
        disp = escolher("Disponibilidade", Disponibilidade, permitir_vazio=True)
        if disp:
            u.disponibilidade = disp
        print("  ✓ Usuário atualizado.")

    # ============================ cargos ============================
    def gerenciar_cargos(self):
        """Os cargos são fixos (Gestor e Técnico); o gestor só ajusta as permissões de cada um."""
        self.usuario.exigir("gerir_usuarios")
        while True:
            titulo("PERMISSÕES DOS CARGOS")
            for c in self.repo.cargos:
                print(f"\n  [{c.id}] {c.nome}")
                for acesso in c.permissoes.ativas():
                    print(f"      • {Permissoes.DESCRICOES[acesso]}")
            print("\n  1. Editar permissões de um cargo  0. Voltar")
            op = ler_int("Opção")
            if op == 0:
                return
            if op != 1:
                continue
            cargo = escolher("Cargo", self.repo.cargos)
            try:
                self._editar_permissoes(cargo)
            except RegraNegocioError as erro:
                print(f"  ! {erro}")
            self.repo.salvar()

    def _editar_permissoes(self, cargo: Cargo):
        acessos = list(Permissoes.DESCRICOES)
        print(f"\n  Permissões de '{cargo.nome}' ([x] = liberada):")
        for i, a in enumerate(acessos, 1):
            marca = "x" if cargo.permissoes.tem(a) else " "
            print(f"   [{marca}] {i:>2}. {Permissoes.DESCRICOES[a]}")
        txt = ler("Números das permissões liberadas, separados por vírgula (ENTER mantém)",
                  obrigatorio=False)
        if not txt:
            return
        try:
            selecao = [acessos[int(x) - 1] for x in txt.split(",") if x.strip()]
        except (ValueError, IndexError):
            raise RegraNegocioError("Seleção de permissões inválida.")
        if cargo is self.usuario.cargo and "gerir_usuarios" not in selecao:
            raise RegraNegocioError("Você não pode remover do seu próprio cargo o acesso de gestão.")
        cargo.permissoes.definir(selecao)
        print(f"  ✓ Permissões do cargo '{cargo.nome}' atualizadas.")
