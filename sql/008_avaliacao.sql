-- Conjunto fixo de tickets usados como consulta na avaliação da busca.
create table if not exists avaliacao_consultas (
    consulta_id  integer primary key,
    sorteado_em  timestamptz not null default now()
);

-- Julgamento manual: o resultado é o mesmo problema da consulta?
create table if not exists avaliacao_busca (
    consulta_id   integer not null,
    resultado_id  integer not null,
    relevante     boolean not null,
    avaliado_em   timestamptz not null default now(),
    primary key (consulta_id, resultado_id)
);