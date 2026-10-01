from datetime import datetime, timedelta, timezone

from copilot_suporte.banco import checar_qualidade, executar_sql, salvar_raw, ultima_atualizacao
from copilot_suporte.movidesk import buscar_historico, buscar_todos
from copilot_suporte.vetores import gerar_vetores

MARGEM = timedelta(minutes=30)  # a API leva alguns minutos para replicar

TRANSFORMACOES = (
    "002_limpo_tickets.sql",
    "003_limpo_acoes.sql",
    "005_limpo_problema.sql",
    "007_limpo_solucoes.sql",
)


def montar_filtro(ultimo: datetime, margem: timedelta = MARGEM) -> str:
    """Filtro OData para buscar só o que mudou desde (ultimo - margem), em UTC."""
    desde = (ultimo - margem).astimezone(timezone.utc)
    filtro = f"lastUpdate gt {desde:%Y-%m-%dT%H:%M:%S}Z"
    return filtro


def executar_carga() -> None:
    """Carga completa na primeira vez; depois, só o que mudou."""
    ultimo = ultima_atualizacao()

    if ultimo is None:
        print("tabela vazia: carga completa")
        tickets = buscar_historico()
    else:
        filtro = montar_filtro(ultimo)
        print("carga incremental:", filtro)
        tickets = buscar_todos(rota="tickets", filtro=filtro)

    salvar_raw(tickets)
    print("gravados:", len(tickets))

    for arquivo in TRANSFORMACOES:
        executar_sql(arquivo)
        print("transformado:", arquivo)

    print("vetores gerados:", gerar_vetores())

    falhas = [(nome, n) for nome, n in checar_qualidade() if n > 0]
    if falhas:
        for nome, n in falhas:
            print(f"  FALHOU: {nome} ({n} problemas)")
        raise RuntimeError(f"{len(falhas)} checagem(ns) de qualidade falharam")
    print("checagens de qualidade: ok")


if __name__ == "__main__":
    executar_carga()