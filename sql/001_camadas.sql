

create table if not exists public.bruto_tickets (
    id            integer primary key,
    last_update   timestamptz not null,
    payload       jsonb not null,
    carregado_em  timestamptz not null default now()
);
