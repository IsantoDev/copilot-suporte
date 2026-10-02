"""Avaliação manual da busca: você julga os resultados, e o script calcula as métricas."""

import argparse

from copilot_suporte.banco import Banco
from copilot_suporte.buscar import Buscador
from copilot_suporte.config import Config
from copilot_suporte.vetorizador import Vetorizador

N_CONSULTAS = 30
K = 5
MAX_POR_CATEGORIA = 3  # as categorias são poucas e grandes: com 3 por categoria saíram só 15 consultas

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
    where ordem <= %s
    order by random()
    limit %s
"""


def consultas(banco: Banco) -> list[int]:
    """O conjunto fixo de consultas; é sorteado só na primeira vez (para comparar modelos na mesma prova)."""
    with banco.conexao() as conn:
        if conn.execute("select count(*) from avaliacao_consultas").fetchone()[0] == 0:
            conn.execute(SQL_SORTEIO, (MAX_POR_CATEGORIA, N_CONSULTAS))
            print("consultas sorteadas")
        return [linha[0] for linha in conn.execute("select consulta_id from avaliacao_consultas order by consulta_id")]


def julgamentos(banco: Banco) -> dict[tuple[int, int], bool]:
    with banco.conexao() as conn:
        linhas = conn.execute("select consulta_id, resultado_id, relevante from avaliacao_busca").fetchall()
    return {(c, r): relevante for c, r, relevante in linhas}


def resumos(banco: Banco, ids: list[int], tamanho: int) -> dict[int, str]:
    with banco.conexao() as conn:
        linhas = conn.execute(
            "select ticket_id, texto from limpo_problemas where ticket_id = any(%s)", (ids,)
        ).fetchall()
    return {ticket_id: " ".join(texto.split())[:tamanho] for ticket_id, texto in linhas}


def gravar(banco: Banco, consulta_id: int, resultado_id: int, relevante: bool) -> None:
    with banco.conexao() as conn:
        conn.execute(
            "insert into avaliacao_busca (consulta_id, resultado_id, relevante) values (%s, %s, %s)",
            (consulta_id, resultado_id, relevante),
        )


def perguntar() -> str:
    while True:
        resposta = input("   mesmo problema? [s/n, p para pular, q para parar] ").strip().lower()
        if resposta in ("s", "n", "p", "q"):
            return resposta


def avaliar(banco: Banco, buscador: Buscador) -> None:
    """Mostra os K resultados de cada consulta e grava o seu julgamento.

    Nenhuma conexão fica emprestada enquanto o programa espera a sua resposta:
    cada leitura e cada gravação pega uma conexão do pool e devolve na hora.
    """
    ids = consultas(banco)
    ja_julgados = julgamentos(banco)

    for numero, consulta_id in enumerate(ids, start=1):
        pendentes = [r for r in buscador.por_ticket(consulta_id, K) or [] if (consulta_id, r.ticket_id) not in ja_julgados]
        if not pendentes:
            continue

        textos = resumos(banco, [consulta_id] + [r.ticket_id for r in pendentes], 500)
        print(f"\n{'=' * 80}\nCONSULTA {numero}/{len(ids)} · problema de referência #{consulta_id}")
        print(textos[consulta_id])
        for r in pendentes:
            print(f"\n   → candidato #{r.ticket_id} ({r.similaridade:.2f}) {textos[r.ticket_id][:300]}")
            resposta = perguntar()
            if resposta == "q":
                print("parado. Rode de novo para continuar de onde parou.")
                return
            if resposta == "p":
                continue
            gravar(banco, consulta_id, r.ticket_id, resposta == "s")


def relatorio(banco: Banco, buscador: Buscador) -> None:
    """Precisão nos K primeiros, acerto no 1º resultado e MRR, com os julgamentos já feitos."""
    ids = consultas(banco)
    ja_julgados = julgamentos(banco)

    precisoes, acertos_no_primeiro, reciprocos, faltando = [], [], [], 0
    for consulta_id in ids:
        resultados = buscador.por_ticket(consulta_id, K) or []
        relevancias = [ja_julgados.get((consulta_id, r.ticket_id)) for r in resultados]
        if not relevancias or None in relevancias:
            faltando += 1
            continue
        precisoes.append(sum(relevancias) / K)
        acertos_no_primeiro.append(relevancias[0])
        primeira = next((i for i, relevante in enumerate(relevancias, start=1) if relevante), None)
        reciprocos.append(1 / primeira if primeira else 0)

    n = len(precisoes)
    print(f"modelo: {buscador.vetorizador.nome}")
    print(f"consultas avaliadas: {n} de {len(ids)}" + (f" ({faltando} com julgamento incompleto)" if faltando else ""))
    if n:
        print(f"precisão nos {K} primeiros: {sum(precisoes) / n:.1%}")
        print(f"acerto no 1º resultado:    {sum(acertos_no_primeiro) / n:.1%}")
        print(f"MRR:                       {sum(reciprocos) / n:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Avaliação manual da busca de tickets parecidos.")
    parser.add_argument("--relatorio", action="store_true", help="só calcula as métricas")
    args = parser.parse_args()
    with Banco() as banco:
        buscador = Buscador(banco, Vetorizador(Config().modelo))
        if args.relatorio:
            relatorio(banco, buscador)
        else:
            avaliar(banco, buscador)


if __name__ == "__main__":
    main()
