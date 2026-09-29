import re
import sys

from sentence_transformers import SentenceTransformer

from copilot_suporte.vetores import MODELO, conectar

SQL_BUSCA = """
    select v.ticket_id,
           1 - (v.embedding <=> %(consulta)s) as similaridade,
           t.assunto,
           s.solucao_publica,
           s.solucao_interna
    from vetores_problemas v
    join limpo_tickets t on t.ticket_id = v.ticket_id
    join limpo_solucoes s on s.ticket_id = v.ticket_id
    where v.modelo = %(modelo)s
    order by v.embedding <=> %(consulta)s
    limit %(k)s
"""

TEXTO_PADRAO = re.compile(
    r"valide a solução|pesquisa de satisfação|qualquer dúvida|atenciosamente",
    re.IGNORECASE,
)


def limpar(texto: str | None) -> str:
    """Remove linhas vazias e as frases padrão do encerramento de chamado."""
    if not texto:
        return ""
    linhas = [linha.strip() for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha and not TEXTO_PADRAO.search(linha))


def buscar_parecidos(texto: str, k: int = 5) -> list[tuple]:
    """Devolve os k tickets resolvidos mais parecidos com o texto."""
    modelo = SentenceTransformer(MODELO)
    consulta = modelo.encode_query(texto, normalize_embeddings=True)
    with conectar() as conn:
        return conn.execute(SQL_BUSCA, {"consulta": consulta, "modelo": MODELO, "k": k}).fetchall()


if __name__ == "__main__":
    texto = " ".join(sys.argv[1:])
    for ticket_id, similaridade, assunto, publica, interna in buscar_parecidos(texto):
        print(f"\n#{ticket_id} · similaridade {similaridade:.2f} · {assunto}")
        print("  para o cliente:", limpar(publica)[:300])
        if interna:
            print("  técnico:", limpar(interna)[:300])