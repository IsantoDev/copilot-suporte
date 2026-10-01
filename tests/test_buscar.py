from copilot_suporte.buscar import limpar, numero_para_id


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