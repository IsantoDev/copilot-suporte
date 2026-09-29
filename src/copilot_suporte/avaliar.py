import argparse

from copilot_suporte.buscar import buscar_parecidos, vetor_do_ticket
from copilot_suporte.vetores import MODELO, conectar

N_CONSULTAS = 30
K = 5

SQL_SORTEIO = """
    insert into avaliacao_consultas (consulta_id)
    select ticket_id
    from (
        select s.ticket_id,
               row_number() over (partition by t.categoria order by random()) as ordem
        from limpo_solucoes s
        join limpo_tickets t on t.ticket_id = s.ticket_id
        join vetores_problemas v on v.ticket_id = s.ticket_id
    ) sorteio
    where ordem <= 3
    order by random()
    limit %s
"""


def consultas(conn) -> list[int]:
    """Devolve o conjunto fixo de consultas; sorteia na primeira vez."""
    if conn.execute("select count(*) from avaliacao_consultas").fetchone()[0] == 0:
        conn.execute(SQL_SORTEIO, (N_CONSULTAS,))
        print(f"sorteadas {N_CONSULTAS} consultas")
    return [linha[0] for linha in conn.execute("select consulta_id from avaliacao_consultas order by consulta_id")]


def julgamentos(conn) -> dict[tuple[int, int], bool]:
    linhas = conn.execute("select consulta_id, resultado_id, relevante from avaliacao_busca")
    return {(c, r): relevante for c, r, relevante in linhas}


def resumos(ids: list[int], tamanho: int) -> dict[int, str]:
    """Lê o texto do problema de vários tickets de uma vez, numa conexão curta."""
    with conectar() as conn:
        linhas = conn.execute(
            "select ticket_id, texto from limpo_problemas where ticket_id = any(%s)", (ids,)
        ).fetchall()
    return {ticket_id: " ".join(texto.split())[:tamanho] for ticket_id, texto in linhas}


def gravar(consulta_id: int, resultado_id: int, relevante: bool) -> None:
    """Grava um julgamento numa conexão própria, aberta só para isso."""
    with conectar() as conn:
        conn.execute(
            "insert into avaliacao_busca (consulta_id, resultado_id, relevante) values (%s, %s, %s)",
            (consulta_id, resultado_id, relevante),
        )


def perguntar() -> str:
    while True:
        resposta = input("   mesmo problema? [s/n, p para pular, q para parar] ").strip().lower()
        if resposta in ("s", "n", "p", "q"):
            return resposta


def avaliar() -> None:
    """Mostra os K resultados de cada consulta e grava o seu julgamento.

    Nenhuma conexão fica aberta enquanto o programa espera a sua resposta:
    os textos são lidos antes da pergunta, e cada resposta é gravada à parte.
    """
    with conectar() as conn:
        ids = consultas(conn)
        ja_julgados = julgamentos(conn)

    for numero, consulta_id in enumerate(ids, start=1):
        resultados = buscar_parecidos(vetor_do_ticket(consulta_id), K, consulta_id)
        pendentes = [r for r in resultados if (consulta_id, r[0]) not in ja_julgados]
        if not pendentes:
            continue

        textos = resumos([consulta_id] + [r[0] for r in pendentes], 500)
        print(f"\n{'=' * 80}\nCONSULTA {numero}/{len(ids)} · problema de referência #{consulta_id}")
        print(textos[consulta_id])
        for resultado_id, similaridade, *_ in pendentes:
            print(f"\n   → candidato #{resultado_id} ({similaridade:.2f}) {textos[resultado_id][:300]}")
            resposta = perguntar()
            if resposta == "q":
                print("parado. Rode de novo para continuar de onde parou.")
                return
            if resposta == "p":
                continue
            gravar(consulta_id, resultado_id, resposta == "s")


def relatorio() -> None:
    """Calcula as métricas da busca com os julgamentos já feitos."""
    with conectar() as conn:
        ids = consultas(conn)
        ja_julgados = julgamentos(conn)

    precisoes, acertos_no_primeiro, reciprocos, faltando = [], [], [], 0
    for consulta_id in ids:
        resultados = buscar_parecidos(vetor_do_ticket(consulta_id), K, consulta_id)
        relevancias = [ja_julgados.get((consulta_id, r[0])) for r in resultados]
        if None in relevancias:
            faltando += 1
            continue
        precisoes.append(sum(relevancias) / K)
        acertos_no_primeiro.append(relevancias[0])
        primeira = next((i for i, rel in enumerate(relevancias, start=1) if rel), None)
        reciprocos.append(1 / primeira if primeira else 0)

    n = len(precisoes)
    print(f"modelo: {MODELO}")
    print(f"consultas avaliadas: {n} de {len(ids)}" + (f" ({faltando} com julgamento incompleto)" if faltando else ""))
    if n:
        print(f"precisão nos {K} primeiros: {sum(precisoes) / n:.1%}")
        print(f"acerto no 1º resultado:    {sum(acertos_no_primeiro) / n:.1%}")
        print(f"MRR:                       {sum(reciprocos) / n:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaliação manual da busca de tickets parecidos.")
    parser.add_argument("--relatorio", action="store_true", help="só calcula as métricas")
    if parser.parse_args().relatorio:
        relatorio()
    else:
        avaliar()