"""Pipeline: API do Movidesk → bruto → limpo → vetores → checagens.

Rodado de hora em hora pelo agendador (scripts/carga.bat).
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

MARGEM = timedelta(minutes=30)  # a API leva alguns minutos para refletir as mudanças

TRANSFORMACOES = (
    "002_limpo_tickets.sql",
    "003_limpo_acoes.sql",
    "005_limpo_problema.sql",
    "007_limpo_solucoes.sql",
)


@dataclass
class ResumoExecucao:
    """O que foi possível contar numa execução (fica None o que não chegou a acontecer)."""

    tickets: int | None = None
    vetores: int | None = None
    checagens_com_falha: int | None = None


def montar_filtro(ultimo: datetime, margem: timedelta = MARGEM) -> str:
    """Filtro OData para buscar só o que mudou desde (ultimo - margem), em UTC."""
    desde = (ultimo - margem).astimezone(timezone.utc)
    return f"lastUpdate gt {desde:%Y-%m-%dT%H:%M:%S}Z"


class Pipeline:
    """Recebe o cliente da API, o banco e o vetorizador prontos (injeção de dependência).

    Assim os testes podem passar versões falsas e rodar o pipeline inteiro sem
    internet, sem banco e sem o modelo.
    """

    def __init__(self, cliente, banco, vetorizador, transformacoes: tuple[str, ...] = TRANSFORMACOES):
        self.cliente = cliente
        self.banco = banco
        self.vetorizador = vetorizador
        self.transformacoes = transformacoes

    def rodar(self) -> ResumoExecucao:
        """Executa a carga e registra a execução em execucoes_pipeline, com sucesso ou falha."""
        execucao_id = self.banco.iniciar_execucao()
        resumo = ResumoExecucao()
        status, erro = "falha", None  # falha por padrão: só vira sucesso se chegar ao fim
        try:
            self.executar(resumo)
            status = "sucesso"
            return resumo
        except Exception as e:
            erro = type(e).__name__  # só o nome: a mensagem pode trazer a URL com o token
            raise
        finally:
            try:
                self.banco.finalizar_execucao(execucao_id, status, erro=erro, **asdict(resumo))
            except Exception as falha_no_registro:
                print("não foi possível registrar o fim da execução:", type(falha_no_registro).__name__)
                if erro is None:
                    raise  # sem erro original, a falha do registro é o problema a mostrar
                # com erro original, ele continua subindo: não deixamos o registro escondê-lo

    def executar(self, resumo: ResumoExecucao) -> None:
        """Carga completa na primeira vez; depois, só o que mudou."""
        ultimo = self.banco.ultima_atualizacao()
        if ultimo is None:
            print("tabela vazia: carga completa")
            tickets = self.cliente.buscar_historico()
        else:
            filtro = montar_filtro(ultimo)
            print("carga incremental:", filtro)
            # Só a rota /tickets: o que mudou desde a última carga está, por definição, nos últimos 90 dias.
            tickets = self.cliente.buscar_todos(rota="tickets", filtro=filtro)

        self.banco.salvar_brutos(tickets)
        resumo.tickets = len(tickets)
        print("gravados:", len(tickets))

        for arquivo in self.transformacoes:
            self.banco.executar_sql(arquivo)
            print("transformado:", arquivo)

        resumo.vetores = self.gerar_vetores()
        print("vetores gerados:", resumo.vetores)

        falhas = [(nome, n) for nome, n in self.banco.checar_qualidade() if n > 0]
        resumo.checagens_com_falha = len(falhas)
        if falhas:
            for nome, n in falhas:
                print(f"  FALHOU: {nome} ({n} problemas)")
            raise RuntimeError(f"{len(falhas)} checagem(ns) de qualidade falharam")
        print("checagens de qualidade: ok")

    def gerar_vetores(self) -> int:
        """Vetores só para os tickets novos, com texto alterado ou de outro modelo."""
        pendentes = self.banco.problemas_pendentes(self.vetorizador.nome)
        if not pendentes:
            print("nenhum ticket novo ou alterado")
            return 0

        print(f"gerando {len(pendentes)} vetores com {self.vetorizador.nome}")
        vetores = self.vetorizador.documentos([texto for _, texto, _ in pendentes])
        linhas = [
            (ticket_id, self.vetorizador.nome, texto_hash, vetor)
            for (ticket_id, _, texto_hash), vetor in zip(pendentes, vetores)
        ]
        self.banco.gravar_vetores(linhas)
        return len(linhas)


def main() -> None:
    from copilot_suporte.banco import Banco
    from copilot_suporte.config import Config
    from copilot_suporte.movidesk import ClienteMovidesk
    from copilot_suporte.vetorizador import Vetorizador

    config = Config()
    with Banco() as banco:
        Pipeline(ClienteMovidesk(config.movidesk_token), banco, Vetorizador(config.modelo)).rodar()


if __name__ == "__main__":
    main()
