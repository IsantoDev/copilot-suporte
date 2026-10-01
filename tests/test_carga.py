from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from copilot_suporte.carga import montar_filtro


def test_filtro_subtrai_a_margem_e_converte_para_utc():
    # 12:00 em Brasília = 15:00 UTC; menos 30 minutos de margem = 14:30 UTC
    ultimo = datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert montar_filtro(ultimo) == "lastUpdate gt 2026-09-29T14:30:00Z"


def test_filtro_aceita_outra_margem():
    ultimo = datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert montar_filtro(ultimo, margem=timedelta(hours=2)) == "lastUpdate gt 2026-09-29T13:00:00Z"