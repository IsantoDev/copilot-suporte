from pathlib import Path

from copilot_suporte import banco as modulo_banco

PACOTE = Path(__file__).resolve().parents[1] / "src" / "copilot_suporte"


def _arquivos_com(trecho: str) -> list[str]:
    return sorted(p.name for p in PACOTE.glob("*.py") if trecho in p.read_text(encoding="utf-8"))


def test_pool_usa_tempo_limite_e_senha_direta(monkeypatch):
    recebido = {}

    class PoolFalso:
        def __init__(self, **kwargs):
            recebido.update(kwargs)

    monkeypatch.setenv("PGPASSWORD", "senha-falsa")
    monkeypatch.setattr(modulo_banco, "ConnectionPool", PoolFalso)

    modulo_banco.Banco()

    assert recebido["kwargs"]["connect_timeout"] == 10
    assert recebido["kwargs"]["password"] == "senha-falsa"  # direta, por causa do "£" no Windows


def test_so_o_banco_abre_conexoes():
    # Regra de arquitetura: conexão com o banco só nasce no banco.py.
    assert _arquivos_com("psycopg.connect(") == []
    assert _arquivos_com("ConnectionPool(") == ["banco.py"]


def test_so_o_vetorizador_carrega_o_modelo():
    # Regra de arquitetura: o PyTorch só é importado pelo vetorizador, e de forma preguiçosa.
    assert _arquivos_com("sentence_transformers") == ["vetorizador.py"]
