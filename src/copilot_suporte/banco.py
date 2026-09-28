import psycopg
import os
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()


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

