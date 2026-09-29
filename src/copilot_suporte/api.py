"""API local do copiloto: busca de tickets parecidos pelo navegador.

Rodar com:  uv run fastapi dev src/copilot_suporte/api.py
e abrir     http://127.0.0.1:8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sentence_transformers import SentenceTransformer

from copilot_suporte.buscar import buscar_parecidos, limpar, numero_para_id, vetor_do_ticket
from copilot_suporte.vetores import MODELO

PAGINA = Path(__file__).parent / "static" / "index.html"
# Endereço do Movidesk da empresa, lido do .env para não ficar no repositório público.
MOVIDESK_URL = os.getenv("MOVIDESK_URL", "").rstrip("/")
recursos = {}


def link_do_ticket(protocolo: str) -> str | None:
    return f"{MOVIDESK_URL}/Ticket/EditByProtocol/{protocolo}" if MOVIDESK_URL else None


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # O modelo é carregado UMA vez, quando a API sobe, e não a cada busca.
    recursos["modelo"] = SentenceTransformer(MODELO)
    yield
    recursos.clear()


app = FastAPI(title="Copiloto de Suporte", lifespan=ciclo_de_vida)


@app.get("/", include_in_schema=False)
def pagina():
    return FileResponse(PAGINA)


@app.get("/parecidos")
def parecidos(
    ticket: int | None = Query(None, description="id ou protocolo do ticket"),
    texto: str | None = Query(None, min_length=3, description="descrição do problema"),
    k: int = Query(5, ge=1, le=20, description="quantos resultados"),
):
    """Tickets resolvidos mais parecidos com um ticket ou com um texto."""
    if ticket:
        excluir = numero_para_id(ticket)
        consulta = vetor_do_ticket(excluir)
        if consulta is None:
            raise HTTPException(404, f"ticket {excluir} sem vetor (ainda não foi carregado?)")
    elif texto:
        excluir = -1
        consulta = recursos["modelo"].encode_query(texto, normalize_embeddings=True)
    else:
        raise HTTPException(400, "informe ticket ou texto")

    return [
        {
            "ticket_id": ticket_id,
            "similaridade": round(float(similaridade), 3),
            "assunto": assunto,
            "solucao_publica": limpar(publica),
            "solucao_interna": limpar(interna),
            "protocolo": protocolo,
            "link": link_do_ticket(protocolo),
        }
        for ticket_id, similaridade, assunto, publica, interna, protocolo in buscar_parecidos(consulta, k, excluir)
    ]
