from datetime import datetime, timedelta, timezone

from copilot_suporte.banco import checar_qualidade, executar_sql, salvar_raw, ultima_atualizacao,finalizar_execucao, iniciar_execucao
from copilot_suporte.movidesk import buscar_historico, buscar_todos
from copilot_suporte.vetores import gerar_vetores

MARGEM = timedelta(minutes=30)  

TRANSFORMACOES = (
    "002_limpo_tickets.sql",
    "003_limpo_acoes.sql",
    "005_limpo_problema.sql",
    "007_limpo_solucoes.sql",
)


def rodar() -> None:
    """Executa a carga e registra a execução, com sucesso ou falha."""
    execucao_id = iniciar_execucao()  
    resumo = {}                        
    status = "falha"                    
    erro = None                         
    try:
        executar_carga(resumo)       
        status = "sucesso"             
    except Exception as e:
        erro = type(e).__name__         
        raise                          
    finally:
        finalizar_execucao(execucao_id, status, resumo, erro)  


def montar_filtro(ultimo: datetime, margem: timedelta = MARGEM) -> str:
    """Filtro OData para buscar só o que mudou desde (ultimo - margem), em UTC."""
    desde = (ultimo - margem).astimezone(timezone.utc)
    filtro = f"lastUpdate gt {desde:%Y-%m-%dT%H:%M:%S}Z"
    return filtro


def executar_carga(resumo: dict) -> None:           
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
    resumo["tickets"] = len(tickets)                
    print("gravados:", len(tickets))

    for arquivo in TRANSFORMACOES:
        executar_sql(arquivo)
        print("transformado:", arquivo)

    resumo["vetores"] = gerar_vetores()                  
    print("vetores gerados:", resumo["vetores"])

    falhas = [(nome, n) for nome, n in checar_qualidade() if n > 0]
    resumo["checagens_com_falha"] = len(falhas)
    if falhas:
        for nome, n in falhas:
            print(f"  FALHOU: {nome} ({n} problemas)")
        raise RuntimeError(f"{len(falhas)} checagem(ns) de qualidade falharam")
    print("checagens de qualidade: ok")


if __name__ == "__main__":
    rodar()
