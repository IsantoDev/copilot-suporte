import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from copilot_suporte import banco


load_dotenv()

def conectar() -> psycopg.Connection:
    conn = banco.conectar()
    register_vector(conn)
    return conn

MODELO = "google/embeddinggemma-300m"

SQL_PENDENTES = """
    select p.ticket_id, p.texto, md5(p.texto)
    from limpo_problemas p
    left join vetores_problemas v using (ticket_id)
    where v.ticket_id is null
       or v.texto_hash <> md5(p.texto)
       or v.modelo <> %s
"""

SQL_UPSERT = """
    insert into vetores_problemas (ticket_id, modelo, texto_hash, embedding)
    values (%s, %s, %s, %s)
    on conflict (ticket_id) do update
        set modelo = excluded.modelo,
            texto_hash = excluded.texto_hash,
            embedding = excluded.embedding,
            gerado_em = now()
"""


def conectar() -> psycopg.Connection:
    conn = psycopg.connect(password=os.environ["PGPASSWORD"])
    register_vector(conn)
    return conn


def gerar_vetores() -> int:
    """Gera embeddings só para tickets novos, com texto alterado ou de outro modelo."""
    with conectar() as conn:
        pendentes = conn.execute(SQL_PENDENTES, (MODELO,)).fetchall()

    if not pendentes:
        print("nenhum ticket novo ou alterado")
        return 0

    print(f"gerando {len(pendentes)} vetores com {MODELO}")
    modelo = SentenceTransformer(MODELO)
    textos = [texto for _, texto, _ in pendentes]
    vetores = modelo.encode_document(
        textos, batch_size=16, show_progress_bar=True, normalize_embeddings=True
    )

    linhas = [(tid, MODELO, hash_, vetor) for (tid, _, hash_), vetor in zip(pendentes, vetores)]
    with conectar() as conn:
        conn.cursor().executemany(SQL_UPSERT, linhas)
    return len(linhas)


if __name__ == "__main__":
    print("gravados:", gerar_vetores())