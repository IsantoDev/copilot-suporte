-- Camadas do copiloto, separadas por prefixo no nome da tabela:
--   bruto_*  -> como veio da API (jsonb), nunca alterado pelo tratamento
--   limpo_*  -> tratado em SQL a partir do bruto
-- O usuário do banco não tem permissão para criar schemas, por isso
-- tudo fica no schema public. Rodar uma vez; pode rodar de novo sem erro.

create table if not exists public.bruto_tickets (
    id            integer primary key,
    last_update   timestamptz not null,
    payload       jsonb not null,
    carregado_em  timestamptz not null default now()
);
