from copilot_suporte.buscar import Buscador, Resultado, limpar, numero_para_id


def test_numero_para_id_aceita_o_id():
    assert numero_para_id(2869) == 2869


def test_numero_para_id_aceita_o_protocolo():
    assert numero_para_id(202609002869) == 2869


def test_limpar_remove_frases_padrao_do_encerramento():
    texto = "Olá, tudo certo.\n\nValide a solução proposta.\nAtt.\nAtenciosamente\nEquipe TOTVS Gestão"
    assert limpar(texto) == "Olá, tudo certo."


def test_limpar_nao_remove_palavras_que_comecam_com_att():
    assert limpar("attachment enviado") == "attachment enviado"


def test_limpar_aceita_texto_vazio():
    assert limpar(None) == ""


def test_link_usa_o_protocolo_e_some_sem_endereco():
    r = Resultado(2453, 0.9, "assunto", "", "", "202608002453")
    assert r.link("https://empresa.movidesk.com") == "https://empresa.movidesk.com/Ticket/EditByProtocol/202608002453"
    assert r.link("") is None


# ---------- buscador, com dublês ----------

LINHA = (2771, 0.6712, "Pendência em caixas", "Resolvido.\nAtt.", None, "202609002771")


class BancoFalso:
    def __init__(self, vetor=(0.1, 0.2)):
        self.vetor = vetor
        self.busca = None

    def vetor_do_ticket(self, ticket_id, modelo):
        return self.vetor

    def buscar_parecidos(self, consulta, modelo, k, excluir):
        self.busca = {"consulta": consulta, "k": k, "excluir": excluir}
        return [LINHA]


class VetorizadorFalso:
    nome = "modelo-falso"

    def __init__(self):
        self.consultas = []

    def consulta(self, texto):
        self.consultas.append(texto)
        return (0.9, 0.9)


def test_por_ticket_usa_o_vetor_guardado_e_exclui_o_proprio_ticket():
    banco, vetorizador = BancoFalso(), VetorizadorFalso()
    resultados = Buscador(banco, vetorizador).por_ticket(202609002929)

    assert banco.busca["excluir"] == 2929
    assert vetorizador.consultas == []  # documento × documento: não passa pelo modelo
    assert resultados == [Resultado(2771, 0.671, "Pendência em caixas", "Resolvido.", "", "202609002771")]


def test_por_ticket_sem_vetor_devolve_none():
    assert Buscador(BancoFalso(vetor=None), VetorizadorFalso()).por_ticket(5) is None


def test_por_texto_usa_a_consulta_do_modelo():
    banco, vetorizador = BancoFalso(), VetorizadorFalso()
    Buscador(banco, vetorizador).por_texto("caixa não fecha", k=3)

    assert vetorizador.consultas == ["caixa não fecha"]
    assert banco.busca == {"consulta": (0.9, 0.9), "k": 3, "excluir": -1}
