

drop table if exists limpo_tickets;

create table limpo_tickets as
select
    (payload->>'id')::int                                  as ticket_id,
    payload->>'subject'                                    as assunto,
    payload->>'category'                                   as categoria,
    payload->>'urgency'                                    as urgencia,
    payload->>'baseStatus'                                 as status_base,
    ((payload->>'createdDate') || '+00:00')::timestamptz   as criado_em,
    ((payload->>'lastUpdate')  || '+00:00')::timestamptz   as atualizado_em,
    jsonb_array_length(payload->'actions')                 as qtd_acoes
from bruto_tickets;

alter table limpo_tickets add primary key (ticket_id);
