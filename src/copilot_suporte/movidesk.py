import os

import requests
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://api.movidesk.com/public/v1'
TOKEN = os.getenv('MOVIDESK_TOKEN')


def buscar_tickets(top: int = 5, skip: int = 0, rota: str = "tickets") -> list[dict]:
    """Busca os tickets do Movidesk"""
    if not TOKEN:
        raise RuntimeError("MOVIDESCK_TOKEN não encontrado")

    params = {
        "token": TOKEN,
        "$select": "id,subject,createdDate,category,urgency,baseStatus,lastUpdate",
        "$expand": "actions($select=id,type,origin,description,createdDate;$expand=createdBy($select=id,profileType))",
        "$orderby": "id asc",
        "$top": top,
        "$skip": skip,
    }
    resposta = requests.get(f"{BASE_URL}/{rota}", params=params, timeout=30)

    if not resposta.ok:
        raise RuntimeError(f'Movidesck respondeu {resposta.status_code}')
    return resposta.json()


def buscar_todos(rota: str = 'tickets', por_pagina: int = 100, max_paginas: int | None = None) -> list[dict]:
    """Busca todos os tickets de uma rota (paginado)"""
    todos = []
    skip = 0
    pagina = 1

    while True:
        lote = buscar_tickets(top=por_pagina, skip=skip, rota=rota)
        todos.extend(lote)
        print(f"{rota} · página {pagina}: {len(lote)} tickets, total {len(todos)}")

        if len(lote) < por_pagina:
            break
        if max_paginas and pagina >= max_paginas:
            break

        skip += por_pagina
        pagina += 1
        time.sleep(6)

    return todos        


def buscar_historico(por_pagina: int = 100) -> list[dict]:
    """Busca os tickets das duas rotas e remove duplicados pelo id."""
    recentes = buscar_todos(rota="tickets", por_pagina=por_pagina)
    antigos = buscar_todos(rota="tickets/past", por_pagina=por_pagina)
    print("recentes:", len(recentes), "| antigos:", len(antigos))

    por_id = {}
    for ticket in recentes + antigos:
        id_ticket = ticket["id"]
        guardado = por_id.get(id_ticket)

        if guardado is None or ticket["lastUpdate"] > guardado["lastUpdate"]:
            por_id[id_ticket] = ticket

    duplicados = len(recentes) + len(antigos) - len(por_id)
    print("duplicados removidos:", duplicados)

    return list(por_id.values())

if __name__ == "__main__":
    tickets = buscar_historico()
    ids = [t["id"] for t in tickets]
    print("Total:", len(tickets), "| menor id:", min(ids), "| maior id:", max(ids))
    print("ids repetidos:", len(ids) - len(set(ids)))