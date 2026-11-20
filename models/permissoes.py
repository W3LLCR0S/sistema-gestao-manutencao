"""Classe Permissoes: cada atributo é um acesso (True/False) do cargo."""

from __future__ import annotations


class Permissoes:
    # Nome do acesso -> descrição exibida na tela (a ordem é a mesma dos atributos)
    DESCRICOES = {
        "ver_equipamentos": "Visualizar equipamentos",
        "ver_os": "Consultar ordens de serviço",
        "abrir_os": "Abrir chamados (OS)",
        "ver_disponibilidade": "Consultar disponibilidade dos técnicos",
        "registrar_apontamento": "Incluir apontamentos no histórico",
        "diagnosticar": "Registrar diagnóstico",
        "apontar_reparo": "Registrar horas, intervenções e peças",
        "atualizar_status": "Atualizar status operacional da OS",
        "concluir_os": "Conclusão técnica da OS",
        "gerir_equipamentos": "Cadastrar/editar/inativar/excluir equipamentos",
        "gerir_usuarios": "Gerenciar usuários, cargos e permissões",
        "atribuir_os": "Atribuir/reatribuir OS a técnicos",
        "aprovar_os": "Aprovar, cancelar e encerrar OS",
    }

    def __init__(self,
                 ver_equipamentos: bool = False,
                 ver_os: bool = False,
                 abrir_os: bool = False,
                 ver_disponibilidade: bool = False,
                 registrar_apontamento: bool = False,
                 diagnosticar: bool = False,
                 apontar_reparo: bool = False,
                 atualizar_status: bool = False,
                 concluir_os: bool = False,
                 gerir_equipamentos: bool = False,
                 gerir_usuarios: bool = False,
                 atribuir_os: bool = False,
                 aprovar_os: bool = False):
        # Acessos compartilhados
        self.ver_equipamentos = ver_equipamentos
        self.ver_os = ver_os
        self.abrir_os = abrir_os
        self.ver_disponibilidade = ver_disponibilidade
        self.registrar_apontamento = registrar_apontamento
        # Acessos de técnico
        self.diagnosticar = diagnosticar
        self.apontar_reparo = apontar_reparo
        self.atualizar_status = atualizar_status
        self.concluir_os = concluir_os
        # Acessos de gestor
        self.gerir_equipamentos = gerir_equipamentos
        self.gerir_usuarios = gerir_usuarios
        self.atribuir_os = atribuir_os
        self.aprovar_os = aprovar_os

    # ---------------------------------------------------------------
    def tem(self, acesso: str) -> bool:
        return bool(getattr(self, acesso, False))

    def ativas(self) -> list[str]:
        return [a for a in self.DESCRICOES if self.tem(a)]

    def definir(self, acessos: list[str]) -> None:
        """Liga apenas os acessos informados e desliga os demais."""
        for a in self.DESCRICOES:
            setattr(self, a, a in acessos)

    # ------------------------ perfis padrão ------------------------
    @classmethod
    def _comuns(cls) -> dict:
        return dict(ver_equipamentos=True, ver_os=True, abrir_os=True,
                    ver_disponibilidade=True, registrar_apontamento=True)

    @classmethod
    def padrao_tecnico(cls) -> Permissoes:
        return cls(**cls._comuns(), diagnosticar=True, apontar_reparo=True,
                   atualizar_status=True, concluir_os=True)

    @classmethod
    def padrao_gestor(cls) -> Permissoes:
        return cls(**cls._comuns(), gerir_equipamentos=True, gerir_usuarios=True,
                   atribuir_os=True, aprovar_os=True)

    # ------------------------ persistência ------------------------
    def to_dict(self) -> dict:
        return {a: self.tem(a) for a in self.DESCRICOES}

    @classmethod
    def from_dict(cls, d: dict | list) -> Permissoes:
        # Formato antigo: lista com os nomes dos acessos ativos
        if isinstance(d, (list, tuple, set)):
            d = {a: True for a in d}
        return cls(**{a: bool(d.get(a, False)) for a in cls.DESCRICOES})
