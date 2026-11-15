"""Persistência dos dados em arquivo JSON (dados/dados.json)."""

import json
import os

from app.constantes import PERM_GESTOR, PERM_TECNICO

PASTA_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")
ARQUIVO_DADOS = os.path.join(PASTA_DADOS, "dados.json")


def dados_iniciais():
    """Base de exemplo criada na primeira execução."""
    return {
        "seq": {"usuario": 3, "cargo": 2, "equipamento": 3, "os": 0, "servico": 0},
        "cargos": [
            {"id": 1, "nome": "Gestor", "permissoes": list(PERM_GESTOR)},
            {"id": 2, "nome": "Técnico", "permissoes": list(PERM_TECNICO)},
        ],
        "usuarios": [
            {"id": 1, "nome": "Ana Souza", "cargo_id": 1, "email": "ana@empresa.com",
             "escala": "Seg-Sex 08h-17h", "disponibilidade": "Disponível"},
            {"id": 2, "nome": "Bruno Lima", "cargo_id": 2, "email": "bruno@empresa.com",
             "escala": "Seg-Sex 07h-16h", "disponibilidade": "Disponível"},
            {"id": 3, "nome": "Carla Mendes", "cargo_id": 2, "email": "carla@empresa.com",
             "escala": "Seg-Sex 13h-22h", "disponibilidade": "Disponível"},
        ],
        "equipamentos": [
            {"id": 1, "nome": "Torno CNC", "fabricante": "Romi", "modelo": "GL 240",
             "num_serie": "RM-2021-0457", "setor": "Usinagem", "data_aquisicao": "15/03/2021", "ativo": True},
            {"id": 2, "nome": "Compressor de Ar", "fabricante": "Schulz", "modelo": "CSW 40",
             "num_serie": "SZ-40-11872", "setor": "Utilidades", "data_aquisicao": "02/08/2019", "ativo": True},
            {"id": 3, "nome": "Empilhadeira Elétrica", "fabricante": "Paletrans", "modelo": "PT 1650",
             "num_serie": "PT-1650-0093", "setor": "Logística", "data_aquisicao": "20/01/2023", "ativo": True},
        ],
        "ordens": [],
        "servicos": [],
    }


def carregar():
    if not os.path.exists(ARQUIVO_DADOS):
        dados = dados_iniciais()
        salvar(dados)
        return dados
    with open(ARQUIVO_DADOS, encoding="utf-8") as f:
        return json.load(f)


def salvar(dados):
    os.makedirs(PASTA_DADOS, exist_ok=True)
    tmp = ARQUIVO_DADOS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQUIVO_DADOS)
