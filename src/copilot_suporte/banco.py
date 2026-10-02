"""Acesso ao PostgreSQL: a única parte do projeto que abre conexões com o banco."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

load_dotenv()

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
TEMPO_LIMITE_CONEXAO = 10  # segundos; sem isso uma rede instável segura a carga por horas

SQL_UPSERT_BRUTO = """
    insert into public.bruto_tickets (id, last_update, payload)
    values (%s, %s, %s)
    on conflict (id) do update
        set payload = excluded.payload,
            last_update = excluded.last_update,
            carregado_em = now()
        where excluded.last_update > public.bruto_tickets.last_update
"""

SQL_PENDENTES = """
    select p.ticket_id, p.texto, md5(p.texto)
    from limpo_problemas p
    left join vetores_problemas v using (ticket_id)
    where v.ticket_id is null
       or v.texto_hash <> md5(p.texto)
       or v.modelo <> %s
"""

SQL_UPSERT_VETOR = """
    insert into vetores_problemas (ticket_id, modelo, texto_hash, embedding)
    values (%s, %s, %s, %s)
    on conflict (ticket_id) do update
        set modelo = excluded.modelo,
            texto_hash = excluded.texto_hash,
            embedding = excluded.embedding,
            gerado_em = now()
"""

SQL_BUSCA = """
    select v.ticket_id,
           1 - (v.embedding <=> %(consulta)s) as similaridade,
           t.assunto,
           s.solucao_publica,
           s.solucao_interna,
           -- protocolo do Movidesk: ano e mês de abertura (horário de Brasília) + id com 6 dígitos
           to_char(t.criado_em at time zone 'America/Sao_Paulo', 'YYYYMM')
               || lpad(t.ticket_id::text, 6, '0') as protocolo
    from vetores_problemas v
    join limpo_tickets t on t.ticket_id = v.ticket_id
    join limpo_solucoes s on s.ticket_id = v.ticket_id
    where v.modelo = %(modelo)s
      and v.ticket_id <> %(excluir)s
    order by v.embedding <=> %(consulta)s
    limit %(k)s
"""

SQL_FINALIZAR = """
    update public.execucoes_pipeline
       set terminado_em = now(), status = %s, tickets = %s,
           vetores = %s, checagens_com_falha = %s, erro = %s
     where id = %s
"""


def _preparar_conexao(conn) -> None:
    """Roda em cada conexão nova do pool: ensina o psycopg a ler e gravar o tipo vector."""
    register_vector(conn)
    conn.commit()  # o pool exige a conexão ociosa, e o register_vector faz uma consulta


class Banco:
    """Pool de conexões + todas as consultas do projeto.

    O pool mantém conexões abertas e as reaproveita. Abrir uma conexão nova com a
    DigitalOcean custa segundos (negociação de SSL); pegar uma do pool custa milissegundos.
    """

    def __init__(self, tamanho_max: int = 4):
        self._pool = ConnectionPool(
            # A senha vai direto (e não pela variável de ambiente PGPASSWORD) porque, no Windows,
            # a libpq lê o ambiente em cp1252 e corrompe o "£" da senha. Host, usuário e banco
            # continuam vindo das variáveis PG* do .env.
            kwargs={"password": os.environ["PGPASSWORD"], "connect_timeout": TEMPO_LIMITE_CONEXAO},
            min_size=1,
            max_size=tamanho_max,
            configure=_preparar_conexao,
            name="copiloto",
            open=True,
        )

    def __enter__(self) -> "Banco":
        return self

    def __exit__(self, *erro) -> None:
        self.fechar()

    def fechar(self) -> None:
        self._pool.close()

    def conexao(self):
        """Empresta uma conexão do pool; ao sair do with, faz commit (ou rollback se der erro)."""
        return self._pool.connection()

    # ---------- camada bruta e transformações ----------

    def salvar_brutos(self, tickets: list[dict]) -> None:
        """Grava os tickets como vieram da API. Só atualiza se a versão for mais nova."""
        # A API manda as datas em UTC sem fuso; o "+00:00" declara isso explicitamente.
        linhas = [(t["id"], t["lastUpdate"] + "+00:00", Jsonb(t)) for t in tickets]
        with self.conexao() as conn:
            conn.cursor().executemany(SQL_UPSERT_BRUTO, linhas)

    def ultima_atualizacao(self):
        """A marca d'água da carga incremental: o maior last_update gravado, ou None."""
        with self.conexao() as conn:
            return conn.execute("select max(last_update) from public.bruto_tickets").fetchone()[0]

    def executar_sql(self, nome_arquivo: str) -> None:
        """Executa um arquivo da pasta sql/ numa transação só (a tabela nunca fica pela metade)."""
        sql = (SQL_DIR / nome_arquivo).read_text(encoding="utf-8")
        with self.conexao() as conn:
            conn.execute(sql)

    def checar_qualidade(self) -> list[tuple[str, int]]:
        """Roda sql/004_checagens.sql e devolve (checagem, problemas)."""
        sql = (SQL_DIR / "004_checagens.sql").read_text(encoding="utf-8")
        with self.conexao() as conn:
            return conn.execute(sql).fetchall()

    # ---------- registro de execuções ----------

    def iniciar_execucao(self) -> int:
        with self.conexao() as conn:
            return conn.execute(
                "insert into public.execucoes_pipeline default values returning id"
            ).fetchone()[0]

    def finalizar_execucao(
        self,
        execucao_id: int,
        status: str,
        *,
        tickets: int | None = None,
        vetores: int | None = None,
        checagens_com_falha: int | None = None,
        erro: str | None = None,
    ) -> None:
        with self.conexao() as conn:
            conn.execute(SQL_FINALIZAR, (status, tickets, vetores, checagens_com_falha, erro, execucao_id))

    # ---------- vetores e busca ----------

    def problemas_pendentes(self, modelo: str) -> list[tuple[int, str, str]]:
        """Tickets sem vetor, com texto alterado (md5 diferente) ou com vetor de outro modelo."""
        with self.conexao() as conn:
            return conn.execute(SQL_PENDENTES, (modelo,)).fetchall()

    def gravar_vetores(self, linhas: list[tuple]) -> None:
        with self.conexao() as conn:
            conn.cursor().executemany(SQL_UPSERT_VETOR, linhas)

    def vetor_do_ticket(self, ticket_id: int, modelo: str):
        """O vetor de documento já guardado de um ticket, ou None."""
        with self.conexao() as conn:
            linha = conn.execute(
                "select embedding from vetores_problemas where ticket_id = %s and modelo = %s",
                (ticket_id, modelo),
            ).fetchone()
        return linha[0] if linha else None

    def buscar_parecidos(self, consulta, modelo: str, k: int, excluir: int) -> list[tuple]:
        parametros = {"consulta": consulta, "modelo": modelo, "k": k, "excluir": excluir}
        with self.conexao() as conn:
            return conn.execute(SQL_BUSCA, parametros).fetchall()

    def saude(self) -> bool:
        """Confere se o banco responde (usado pela rota /saude da API)."""
        with self.conexao() as conn:
            return conn.execute("select 1").fetchone()[0] == 1
