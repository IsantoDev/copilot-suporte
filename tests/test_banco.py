from pathlib import Path

from copilot_suporte import vetores

PACOTE = Path(__file__).resolve().parents[1] / "src" / "copilot_suporte"


def test_conexao_dos_vetores_tem_tempo_limite(monkeypatch):
    recebido = {}
    monkeypatch.setattr("psycopg.connect", lambda **kwargs: recebido.update(kwargs) or object())
    monkeypatch.setattr(vetores, "register_vector", lambda conn: None)

    vetores.conectar()

    assert recebido.get("connect_timeout") == 10


def test_so_o_banco_abre_conexao_direto():
    arquivos = [p.name for p in PACOTE.glob("*.py") if "psycopg.connect(" in p.read_text(encoding="utf-8")]
    assert arquivos == ["banco.py"]