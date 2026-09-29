-- Solução de cada ticket resolvido: a última mensagem pública do agente
-- e a última nota interna do agente (onde costuma ficar o detalhe técnico).

drop table if exists limpo_solucoes;

create table limpo_solucoes as
with ultimas as (
    select distinct on (ticket_id, visibilidade)
        ticket_id, visibilidade, descricao
    from limpo_acoes
    where autor_perfil = 'agente'
      and nullif(trim(descricao), '') is not null
    order by ticket_id, visibilidade, (length(trim(descricao)) >= 30) desc, acao_id desc
)
select
    t.ticket_id,
    max(u.descricao) filter (where u.visibilidade = 'publica') as solucao_publica,
    max(u.descricao) filter (where u.visibilidade = 'interna') as solucao_interna
from limpo_tickets t
join ultimas u on u.ticket_id = t.ticket_id
where t.status_base in ('Resolved', 'Closed')
group by t.ticket_id;

alter table limpo_solucoes add primary key (ticket_id);