"""Contexto da aplicação: dados carregados, usuário logado e funções auxiliares
usadas por todos os módulos."""

from app import persistencia
from app.constantes import STATUS_FINAIS
from app.entrada import agora


class Contexto:
    def __init__(self):
        self.db = persistencia.carregar()
        self.usuario = None

    def salvar(self):
        persistencia.salvar(self.db)

    # ------------------------- consultas -------------------------
    def prox_id(self, chave):
        self.db["seq"][chave] += 1
        return self.db["seq"][chave]

    def buscar(self, colecao, valor, campo="id"):
        return next((x for x in self.db[colecao] if x[campo] == valor), None)

    def cargo_de(self, usuario):
        return self.buscar("cargos", usuario["cargo_id"])

    def nome_usuario(self, uid):
        u = self.buscar("usuarios", uid)
        return u["nome"] if u else "—"

    def nome_equip(self, eid):
        e = self.buscar("equipamentos", eid)
        return e["nome"] if e else "(excluído)"

    # ------------------------- permissões -------------------------
    def pode(self, permissao, usuario=None):
        u = usuario or self.usuario
        cargo = self.cargo_de(u)
        return bool(cargo) and permissao in cargo["permissoes"]

    def tecnicos(self):
        return [u for u in self.db["usuarios"] if self.pode("apontar_reparo", u)]

    def carga(self, tid):
        """Quantidade de OS ativas atribuídas ao técnico."""
        return sum(1 for o in self.db["ordens"]
                   if o["tecnico_id"] == tid and o["status"] not in STATUS_FINAIS)

    # ------------------------- histórico (Serviço) -------------------------
    def registrar_servico(self, os_, tipo, descricao):
        """Registro sequencial do histórico de intervenções."""
        self.db["servicos"].append({
            "id": self.prox_id("servico"),
            "os_numero": os_["numero"],
            "equipamento_id": os_["equipamento_id"],
            "usuario_id": self.usuario["id"],
            "data": agora(),
            "tipo": tipo,
            "descricao": descricao,
        })

    def atualizar_disponibilidade(self, tid):
        """Técnico com OS em execução fica 'Em atendimento'; senão 'Disponível'.
        Quem está 'Ausente' só muda manualmente."""
        u = self.buscar("usuarios", tid)
        if not u or u["disponibilidade"] == "Ausente":
            return
        em_campo = any(o["tecnico_id"] == tid and o["status"] == "Em Execução" for o in self.db["ordens"])
        u["disponibilidade"] = "Em atendimento" if em_campo else "Disponível"
