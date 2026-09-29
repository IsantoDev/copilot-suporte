-- Cada linha é uma checagem: "problemas" > 0 faz o pipeline parar.

select 'limpo_tickets diferente do bruto' as checagem,
       abs((select count(*) from limpo_tickets) - (select count(*) from bruto_tickets)) as problemas

union all
select 'limpo_acoes diferente do bruto',
       abs((select count(*) from limpo_acoes)
         - (select sum(jsonb_array_length(payload->'actions')) from bruto_tickets))

union all
select 'ticket sem nenhuma ação',
       count(*) from limpo_tickets where qtd_acoes = 0

union all
select 'data no futuro',
       count(*) from limpo_acoes where criado_em > now() + interval '1 hour'

union all
select 'ação anterior à abertura do ticket',
       count(*)
from limpo_acoes a
join limpo_tickets t using (ticket_id)
where a.criado_em < t.criado_em - interval '1 minute'

union all
select 'dados parados há mais de 3 dias',
       case when (select max(atualizado_em) from limpo_tickets) < now() - interval '3 days'
            then 1 else 0 end

union all
select 'ticket fechado sem categoria',
       count(*)
from limpo_tickets
where status_base in ('Closed', 'Resolved')
  and categoria is null

union all
select 'ticket sem vetor atualizado',
       count(*)
from limpo_problemas p
left join vetores_problemas v on v.ticket_id = p.ticket_id
where v.ticket_id is null
   or v.texto_hash <> md5(p.texto);