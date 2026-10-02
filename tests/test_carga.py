from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from copilot_suporte.carga import Pipeline, montar_filtro


# ---------- filtro da carga incremental ----------

def test_filtro_subtrai_a_margem_e_converte_para_utc():
    # 12:00 em Brasília = 15:00 UTC; menos 30 minutos de margem = 14:30 UTC
    ultimo = datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert montar_filtro(ultimo) == "lastUpdate gt 2026-09-29T14:30:00Z"


def test_filtro_aceita_outra_margem():
    ultimo = datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert montar_filtro(ultimo, margem=timedelta(hours=2)) == "lastUpdate gt 2026-09-29T13:00:00Z"


# ---------- pipeline inteiro, com dublês no lugar da API, do banco e do modelo ----------

class ClienteFalso:
    def __init__(self, tickets=None, erro=None):
        self.tickets = tickets if tickets is not None else [{"id": 1, "lastUpdate": "2026-10-01T10:00:00"}]
        self.erro = erro
        self.chamadas = []

    def buscar_todos(self, rota, filtro):
        self.chamadas.append(("incremental", rota, filtro))
        if self.erro:
            raise self.erro
        return self.tickets

    def buscar_historico(self):
        self.chamadas.append(("completa",))
        return self.tickets


class BancoFalso:
    def __init__(self, ultimo=datetime(2026, 10, 1, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo")), checagens=None):
        self.ultimo = ultimo
        self.checagens = checagens if checagens is not None else [("data no futuro", 0)]
        self.sql_executados = []
        self.vetores_gravados = []
        self.final = None

    def iniciar_execucao(self):
        return 42

    def finalizar_execucao(self, execucao_id, status, **campos):
        self.final = {"id": execucao_id, "status": status, **campos}

    def ultima_atualizacao(self):
        return self.ultimo

    def salvar_brutos(self, tickets):
        self.brutos = tickets

    def executar_sql(self, arquivo):
        self.sql_executados.append(arquivo)

    def problemas_pendentes(self, modelo):
        return [(1, "caixa com pendência", "hash1")]

    def gravar_vetores(self, linhas):
        self.vetores_gravados = linhas

    def checar_qualidade(self):
        return self.checagens


class VetorizadorFalso:
    nome = "modelo-falso"

    def documentos(self, textos):
        return [[0.1, 0.2] for _ in textos]


def test_execucao_completa_registra_sucesso_com_as_contagens():
    banco = BancoFalso()
    cliente = ClienteFalso()

    Pipeline(cliente, banco, VetorizadorFalso(), transformacoes=("002.sql", "003.sql")).rodar()

    assert cliente.chamadas == [("incremental", "tickets", "lastUpdate gt 2026-10-01T14:30:00Z")]
    assert banco.sql_executados == ["002.sql", "003.sql"]
    assert banco.vetores_gravados == [(1, "modelo-falso", "hash1", [0.1, 0.2])]
    assert banco.final == {"id": 42, "status": "sucesso", "erro": None,
                           "tickets": 1, "vetores": 1, "checagens_com_falha": 0}


def test_tabela_vazia_faz_a_carga_completa():
    cliente = ClienteFalso()
    Pipeline(cliente, BancoFalso(ultimo=None), VetorizadorFalso(), transformacoes=()).rodar()
    assert cliente.chamadas == [("completa",)]


def test_checagem_com_problema_registra_falha_e_para():
    banco = BancoFalso(checagens=[("data no futuro", 3), ("ticket sem ação", 0)])
    with pytest.raises(RuntimeError, match="1 checagem"):
        Pipeline(ClienteFalso(), banco, VetorizadorFalso(), transformacoes=()).rodar()
    assert banco.final["status"] == "falha"
    assert banco.final["checagens_com_falha"] == 1
    assert banco.final["erro"] == "RuntimeError"


def test_falha_na_api_registra_falha_com_o_que_deu_para_contar():
    banco = BancoFalso()
    with pytest.raises(ConnectionError):
        Pipeline(ClienteFalso(erro=ConnectionError("fora do ar")), banco, VetorizadorFalso()).rodar()
    assert banco.final["status"] == "falha"
    assert banco.final["erro"] == "ConnectionError"
    assert banco.final["tickets"] is None  # a carga nem chegou a gravar


def test_falha_ao_registrar_o_fim_nao_esconde_o_erro_original():
    class BancoQueCaiNoFim(BancoFalso):
        def finalizar_execucao(self, *args, **kwargs):
            raise OSError("banco caiu")

    with pytest.raises(ConnectionError):  # o erro original, e não o OSError do registro
        Pipeline(ClienteFalso(erro=ConnectionError("fora do ar")), BancoQueCaiNoFim(), VetorizadorFalso()).rodar()
