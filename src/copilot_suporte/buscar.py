"""Busca de tickets resolvidos parecidos, por número de ticket ou por texto."""

import argparse
import re
from dataclasses import dataclass

TEXTO_PADRAO = re.compile(
    r"valide a solução|pesquisa de satisfação|qualquer dúvida|atenciosamente|^att\b"
    r"|horário de atendimento|^equipe totvs|guiados pela",
    re.IGNORECASE,
)


def limpar(texto: str | None) -> str:
    """Remove linhas vazias, assinaturas e frases padrão do encerramento de chamado."""
    if not texto:
        return ""
    linhas = [linha.strip() for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha and not TEXTO_PADRAO.search(linha))


def numero_para_id(numero: int) -> int:
    """Aceita o id (2869) ou o protocolo do Movidesk (202609002869)."""
    return int(str(numero)[-6:]) if numero > 999_999 else numero


@dataclass(frozen=True)
class Resultado:
    ticket_id: int
    similaridade: float
    assunto: str | None
    solucao_publica: str
    solucao_interna: str
    protocolo: str

    def link(self, movidesk_url: str) -> str | None:
        return f"{movidesk_url}/Ticket/EditByProtocol/{self.protocolo}" if movidesk_url else None


class Buscador:
    def __init__(self, banco, vetorizador):
        self.banco = banco
        self.vetorizador = vetorizador

    def por_ticket(self, numero: int, k: int = 5) -> list[Resultado] | None:
        """Documento × documento: usa o vetor já guardado, sem carregar o modelo.

        Devolve None se o ticket ainda não tem vetor (quem chama decide o que fazer).
        """
        ticket_id = numero_para_id(numero)
        consulta = self.banco.vetor_do_ticket(ticket_id, self.vetorizador.nome)
        if consulta is None:
            return None
        return self._buscar(consulta, k, excluir=ticket_id)

    def por_texto(self, texto: str, k: int = 5) -> list[Resultado]:
        """Pergunta × documento: o texto digitado vira vetor de consulta."""
        return self._buscar(self.vetorizador.consulta(texto), k, excluir=-1)

    def _buscar(self, consulta, k: int, excluir: int) -> list[Resultado]:
        linhas = self.banco.buscar_parecidos(consulta, self.vetorizador.nome, k, excluir)
        return [
            Resultado(ticket_id, round(float(similaridade), 3), assunto, limpar(publica), limpar(interna), protocolo)
            for ticket_id, similaridade, assunto, publica, interna, protocolo in linhas
        ]


def main() -> None:
    from copilot_suporte.banco import Banco
    from copilot_suporte.config import Config
    from copilot_suporte.vetorizador import Vetorizador

    parser = argparse.ArgumentParser(description="Busca tickets resolvidos parecidos.")
    parser.add_argument("texto", nargs="*", help="descrição do problema")
    parser.add_argument("--ticket", type=int, help="id ou protocolo do ticket")
    parser.add_argument("-k", type=int, default=5, help="quantos resultados mostrar")
    args = parser.parse_args()
    if not args.ticket and not args.texto:
        parser.error("informe um texto ou --ticket")

    with Banco() as banco:
        buscador = Buscador(banco, Vetorizador(Config().modelo))
        if args.ticket:
            resultados = buscador.por_ticket(args.ticket, args.k)
            if resultados is None:
                raise SystemExit(f"ticket {numero_para_id(args.ticket)} sem vetor (ainda não foi carregado?)")
        else:
            resultados = buscador.por_texto(" ".join(args.texto), args.k)

    for r in resultados:
        print(f"\n#{r.ticket_id} ({r.protocolo}) · similaridade {r.similaridade:.2f} · {r.assunto}")
        print("  para o cliente:", r.solucao_publica[:300])
        if r.solucao_interna:
            print("  técnico:", r.solucao_interna[:300])


if __name__ == "__main__":
    main()
