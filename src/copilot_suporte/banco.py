import psycopg
import os
from pathlib import Path
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()
SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

SQL_UPSERT = """
    insert into public.bruto_tickets (id, last_update, payload)
    values (%s, %s, %s)
    on conflict (id) do update
        set payload = excluded.payload,
            last_update = excluded.last_update,
            carregado_em = now()
        where excluded.last_update > public.bruto_tickets.last_update
"""


def salvar_raw(tickets: list[dict]) -> None:
    """Grava os tickets brutos. Só atualiza se a versão for mais nova."""
    linhas = [
        (t["id"], t["lastUpdate"] + "+00:00", Jsonb(t))
        for t in tickets
    ]
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        with conn.cursor() as cur:
            cur.executemany(SQL_UPSERT, linhas)


def ultima_atualizacao():
    """Retorna o maior last_update gravado, ou None se a tabela estiver vazia."""
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        return conn.execute("select max(last_update) from public.bruto_tickets").fetchone()[0]
    

def executar_sql(nome_arquivo: str) -> None:
    """Executa um arquivo .sql da pasta sql/ numa transação só."""
    sql = (SQL_DIR / nome_arquivo).read_text(encoding="utf-8")
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        conn.execute(sql)


def checar_qualidade() -> list[tuple[str, int]]:
    """Roda sql/004_checagens.sql e devolve (checagem, problemas)."""
    sql = (SQL_DIR / "004_checagens.sql").read_text(encoding="utf-8")
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        return conn.execute(sql).fetchall()

def iniciar_execucao() -> int:
    """Registra o início de uma execução e devolve o id dela."""
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        return conn.execute(
            "insert into public.execucoes_pipeline default values returning id"
        ).fetchone()[0]


def finalizar_execucao(execucao_id: int, status: str, resumo: dict, erro: str | None = None) -> None:
    """Fecha a execução com o status final e o que foi possível contar."""
    with psycopg.connect(password=os.environ["PGPASSWORD"]) as conn:
        conn.execute(
            """
            update public.execucoes_pipeline
               set terminado_em = now(), status = %s, tickets = %s,
                   vetores = %s, checagens_com_falha = %s, erro = %s
             where id = %s
            """,
            (status, resumo.get("tickets"), resumo.get("vetores"),
             resumo.get("checagens_com_falha"), erro, execucao_id),
        )
