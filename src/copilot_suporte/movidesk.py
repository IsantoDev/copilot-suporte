import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://api.movidesk.com/public/v1'
TOKEN = os.getenv('MOVIDESK_TOKEN')

def buscar_ticket(top: int = 1) -> list[dict]:
    """Busca os primeiro tickets do Movidesk, com as ações"""
    if not TOKEN:
        raise RuntimeError("MOVIDESCK_TOKEN não encontrado")

    params = {
        "token": TOKEN,
        "$select": "id,subject,createdDate,category,urgency,baseStatus,lastUpdate",
        "$expand": "actions($select=id,type,origin,description,createdDate;$expand=createdBy($select=id,profileType))",
        "$orderby": "id asc",
        "$top": top,
    }
    resposta = requests.get(f"{BASE_URL}/tickets", params=params, timeout=30)

    if not resposta.ok:
        raise RuntimeError(f'Movidesck respondeu {resposta.status_code}')
    return resposta.json()

if __name__ == '__main__':
    tickets = buscar_ticket()
    print(len(tickets), "tickets recebidos")

    primeiro = tickets[0]
    print("Chave do ticket:", list(primeiro.keys()))
    if primeiro.get('actions'):
        print("Chaves de uma ação:", list(primeiro['actions'][0].keys()))
    print("Menor id:", primeiro["id"], "| criado em:", primeiro["createdDate"])
    print("Chaves do createdBy:", list(primeiro["actions"][0]["createdBy"].keys()))