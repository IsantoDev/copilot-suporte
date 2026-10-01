import os

import requests
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://api.movidesk.com/public/v1'
TOKEN = os.getenv('MOVIDESK_TOKEN')
TENTATIVAS = 3

def buscar_tickets(top: int = 5, skip: int = 0, rota: str = "tickets", filtro: str | None = None) -> list[dict]:
    """Busca uma página de tickets do Movidesk, com até 3 tentativas."""
    if not TOKEN:
        raise RuntimeError("MOVIDESK_TOKEN não encontrado no .env")

    params = {
        "token": TOKEN,
        "$select": "id,subject,createdDate,category,urgency,baseStatus,lastUpdate",
        "$expand": "actions($select=id,type,origin,description,createdDate;$expand=createdBy($select=id,profileType))",
        "$orderby": "id asc",
        "$top": top,
        "$skip": skip,
    }
    if filtro:
        params["$filter"] = filtro

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(f"{BASE_URL}/{rota}", params=params, timeout=60)
        except requests.RequestException as erro:
            motivo = type(erro).__name__
            espera = 30 * tentativa
        else:
            if resposta.ok:
                return resposta.json()
            if resposta.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Movidesk respondeu {resposta.status_code}")
            motivo = f"status {resposta.status_code}"
            espera = int(resposta.headers.get("retry-after", 30 * tentativa))

        print(f"  falha ({motivo}) · tentativa {tentativa}/{TENTATIVAS} · esperando {espera}s")
        time.sleep(espera)

    raise RuntimeError(f"Movidesk falhou {TENTATIVAS} vezes seguidas ({motivo})")

def buscar_todos(rota: str = 'tickets', por_pagina: int = 100, max_paginas: int | None = None, filtro: str | None = None) -> list[dict]:
    """Busca todos os tickets de uma rota (paginado)"""
    todos = []
    skip = 0
    pagina = 1

    while True:
        lote = buscar_tickets(top=por_pagina, skip=skip, rota=rota, filtro=filtro)
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


def juntar_sem_duplicar(*listas: list[dict]) -> list[dict]:
    """Junta listas de tickets; se um id se repete, fica o de lastUpdate mais recente."""
    por_id= {}
    for lista in listas:
        for ticket in lista:
            guardado = por_id.get(ticket['id'])
            if guardado is None or ticket['lastUpdate'] > guardado['lastUpdate']:
                por_id[ticket['id']] = ticket

    return list(por_id.values())
        

def buscar_historico(por_pagina: int = 100) -> list[dict]:
    """Busca os tickets das duas rotas e remove duplicados pelo id."""
    recentes = buscar_todos(rota="tickets", por_pagina=por_pagina)
    antigos = buscar_todos(rota="tickets/past", por_pagina=por_pagina)

    tickets = juntar_sem_duplicar(recentes, antigos)  

    duplicados = len(recentes) + len(antigos) - len(tickets)
    print("recentes:", len(recentes), "| antigos:", len(antigos), "| duplicados removidos:", duplicados)

    return tickets

if __name__ == "__main__":
    tickets = buscar_todos(por_pagina=100)
    ids = [t["id"] for t in tickets]
    print("Total:", len(tickets), "| menor id:", min(ids), "| maior id:", max(ids))
    print("ids repetidos:", len(ids) - len(set(ids)))