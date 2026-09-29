-- Camada limpa: uma linha por ação (mensagem) de cada ticket.
-- O id da ação é sequencial DENTRO do ticket, por isso a chave é (ticket_id, acao_id).

drop table if exists limpo_acoes;

create table limpo_acoes as
select
    (t.payload->>'id')::int                                   as ticket_id,
    (a.acao->>'id')::int                                      as acao_id,
    (a.acao->>'type')::int                                    as tipo,
    case (a.acao->>'type')::int
        when 1 then 'interna'
        when 2 then 'publica'
    end                                                       as visibilidade,
    (a.acao->>'origin')::int                                  as origem,
    a.acao->'createdBy'->>'id'                                as autor_id,
    case (a.acao->'createdBy'->>'profileType')::int
        when 1 then 'agente'
        when 2 then 'cliente'
        when 3 then 'agente e cliente'
    end                                                       as autor_perfil,
    ((a.acao->>'createdDate') || '+00:00')::timestamptz       as criado_em,
    a.acao->>'description'                                    as descricao
from bruto_tickets t
cross join lateral jsonb_array_elements(t.payload->'actions') as a(acao);

alter table limpo_acoes add primary key (ticket_id, acao_id);