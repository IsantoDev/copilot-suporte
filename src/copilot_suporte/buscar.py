import argparse
import re

from sentence_transformers import SentenceTransformer

from copilot_suporte.vetores import MODELO, conectar

SQL_BUSCA = """
    select v.ticket_id,
           1 - (v.embedding <=> %(consulta)s) as similaridade,
           t.assunto,
           s.solucao_publica,
           s.solucao_interna,
           -- protocolo do Movidesk: ano e mês de abertura (horário de Brasília) + id com 6 dígitos
           to_char(t.criado_em at time zone 'America/Sao_Paulo', 'YYYYMM')
               || lpad(t.ticket_id::text, 6, '0') as protocolo
    from vetores_problemas v
    join limpo_tickets t on t.ticket_id = v.ticket_id
    join limpo_solucoes s on s.ticket_id = v.ticket_id
    where v.modelo = %(modelo)s
      and v.ticket_id <> %(excluir)s
    order by v.embedding <=> %(consulta)s
    limit %(k)s
"""

TEXTO_PADRAO = re.compile(
    r"valide a solução|pesquisa de satisfação|qualquer dúvida|atenciosamente|^att\b"
    r"|horário de atendimento|^equipe totvs|guiados pela",
    re.IGNORECASE,
)


def limpar(texto: str | None) -> str:
    """Remove linhas vazias, assinaturas e frases padrão do encerramento de chamado."""
    if not texto:
        return ""
    linhas = [linha.strip() for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha and not TEXTO_PADRAO.search(linha))


def numero_para_id(numero: int) -> int:
    """Aceita o id (2869) ou o protocolo do Movidesk (202609002869)."""
    return int(str(numero)[-6:]) if numero > 999_999 else numero


def vetor_do_ticket(ticket_id: int):
    """Busca o vetor já guardado de um ticket (documento × documento), ou None."""
    with conectar() as conn:
        linha = conn.execute(
            "select embedding from vetores_problemas where ticket_id = %s and modelo = %s",
            (ticket_id, MODELO),
        ).fetchone()
    return linha[0] if linha else None


def vetor_do_texto(texto: str):
    """Transforma um texto digitado em vetor de consulta (pergunta × documento)."""
    modelo = SentenceTransformer(MODELO)
    return modelo.encode_query(texto, normalize_embeddings=True)


def buscar_parecidos(consulta, k: int = 5, excluir: int = -1) -> list[tuple]:
    """Devolve os k tickets resolvidos mais próximos do vetor de consulta."""
    parametros = {"consulta": consulta, "modelo": MODELO, "k": k, "excluir": excluir}
    with conectar() as conn:
        return conn.execute(SQL_BUSCA, parametros).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description="Busca tickets resolvidos parecidos.")
    parser.add_argument("texto", nargs="*", help="descrição do problema")
    parser.add_argument("--ticket", type=int, help="id ou protocolo do ticket")
    parser.add_argument("-k", type=int, default=5, help="quantos resultados mostrar")
    args = parser.parse_args()

    if args.ticket:
        excluir = numero_para_id(args.ticket)
        consulta = vetor_do_ticket(excluir)
        if consulta is None:
            raise SystemExit(f"ticket {excluir} sem vetor (ainda não foi carregado?)")
    elif args.texto:
        excluir = -1
        consulta = vetor_do_texto(" ".join(args.texto))
    else:
        parser.error("informe um texto ou --ticket")

    for ticket_id, similaridade, assunto, publica, interna, protocolo in buscar_parecidos(consulta, args.k, excluir):
        print(f"\n#{ticket_id} ({protocolo}) · similaridade {similaridade:.2f} · {assunto}")
        print("  para o cliente:", limpar(publica)[:300])
        if interna:
            print("  técnico:", limpar(interna)[:300])


if __name__ == "__main__":
    main()