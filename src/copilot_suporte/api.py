"""API local do copiloto: busca de tickets parecidos pelo navegador.

Rodar com:  uv run fastapi dev src/copilot_suporte/api.py
e abrir     http://127.0.0.1:8000   (nunca expor com --host 0.0.0.0: a API devolve dados de clientes)
"""

from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from copilot_suporte.banco import Banco
from copilot_suporte.buscar import Buscador, Resultado
from copilot_suporte.config import Config
from copilot_suporte.vetorizador import Vetorizador

PAGINA = Path(__file__).parent / "static" / "index.html"
recursos: dict = {}


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Tudo nasce uma vez, quando a API sobe: o pool de conexões e o modelo.
    config = Config()
    banco = Banco()
    vetorizador = Vetorizador(config.modelo)
    vetorizador.carregar()  # carrega já, para a primeira busca por texto não esperar
    recursos.update(config=config, banco=banco, vetorizador=vetorizador, buscador=Buscador(banco, vetorizador))
    yield
    banco.fechar()
    recursos.clear()


app = FastAPI(title="Copiloto de Suporte", lifespan=ciclo_de_vida)


def _para_json(resultado: Resultado) -> dict:
    return {**asdict(resultado), "link": resultado.link(recursos["config"].movidesk_url)}


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
    buscador: Buscador = recursos["buscador"]
    if ticket:
        resultados = buscador.por_ticket(ticket, k)
        if resultados is None:
            raise HTTPException(404, "ticket sem vetor (ainda não foi carregado?)")
    elif texto:
        resultados = buscador.por_texto(texto, k)
    else:
        raise HTTPException(400, "informe ticket ou texto")
    return [_para_json(r) for r in resultados]


@app.get("/saude")
def saude():
    """Para o monitoramento: 200 só se o banco responde e o modelo está carregado."""
    try:
        banco_ok = recursos["banco"].saude()
    except Exception:
        banco_ok = False
    modelo_ok = recursos["vetorizador"].carregado
    corpo = {"banco": banco_ok, "modelo": modelo_ok}
    return JSONResponse(corpo, status_code=200 if banco_ok and modelo_ok else 503)
