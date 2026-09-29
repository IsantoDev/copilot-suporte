from datetime import timedelta, timezone

from copilot_suporte.banco import salvar_raw, ultima_atualizacao,executar_sql
from copilot_suporte.movidesk import buscar_historico, buscar_todos

MARGEM = timedelta(minutes=30)  # a API leva alguns minutos para replicar


def executar_carga() -> None:
    """Carga completa na primeira vez; depois, só o que mudou."""
    ultimo = ultima_atualizacao()

    if ultimo is None:
        print("tabela vazia: carga completa")
        tickets = buscar_historico()
    else:
        desde = (ultimo - MARGEM).astimezone(timezone.utc)
        filtro = f"lastUpdate gt {desde:%Y-%m-%dT%H:%M:%S}Z"
        print("carga incremental desde", f"{desde:%d/%m/%Y %H:%M} UTC")
        tickets = buscar_todos(rota="tickets", filtro=filtro)

    salvar_raw(tickets)
    for arquivo in ("002_limpo_tickets.sql", "003_limpo_acoes.sql"):
        executar_sql(arquivo)
        print("transformado:", arquivo)
    print("gravados:", len(tickets))


if __name__ == "__main__":
    executar_carga()
