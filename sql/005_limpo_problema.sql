-- Texto do problema de cada ticket: assunto + mensagens públicas
-- até a primeira resposta do agente (a fase em que o cliente descreve o problema).
-- A primeira mensagem entra sempre, mesmo quando foi um agente que abriu o ticket.

drop table if exists limpo_problemas;

create table limpo_problemas as
with primeira_resposta as (
    select a.ticket_id, min(a.acao_id) as acao_id
    from limpo_acoes a
    where a.autor_perfil = 'agente'
      and a.visibilidade = 'publica'
      and a.acao_id > (select min(b.acao_id) from limpo_acoes b where b.ticket_id = a.ticket_id)
    group by a.ticket_id
)
select
    t.ticket_id,
    concat_ws(
        E'\n\n',
        t.assunto,
        string_agg(nullif(trim(a.descricao), ''), E'\n\n' order by a.acao_id)
    ) as texto
from limpo_tickets t
left join primeira_resposta pr on pr.ticket_id = t.ticket_id
left join limpo_acoes a
       on a.ticket_id = t.ticket_id
      and a.visibilidade = 'publica'
      and (pr.acao_id is null or a.acao_id < pr.acao_id)
group by t.ticket_id, t.assunto;

alter table limpo_problemas add primary key (ticket_id);