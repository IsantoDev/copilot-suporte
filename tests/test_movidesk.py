from copilot_suporte.movidesk import juntar_sem_duplicar

ANTIGO = {"id": 7, "lastUpdate": "2026-09-01T10:00:00"}
NOVO = {"id": 7, "lastUpdate": "2026-09-02T10:00:00"}
OUTRO = {"id": 8, "lastUpdate": "2026-09-01T10:00:00"}


def test_juntar_mantem_a_versao_mais_nova():
    resultado = juntar_sem_duplicar([ANTIGO, OUTRO], [NOVO])
    assert sorted(t["id"] for t in resultado) == [7, 8]
    assert next(t for t in resultado if t["id"] == 7) == NOVO


def test_juntar_nao_depende_da_ordem_das_listas():
    resultado = juntar_sem_duplicar([NOVO], [ANTIGO, OUTRO])
    assert next(t for t in resultado if t["id"] == 7) == NOVO