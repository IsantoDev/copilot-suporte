-- Uma linha por execução do pipeline; o sentinela lê daqui.
create table if not exists public.execucoes_pipeline (
    id                   bigint generated always as identity primary key,
    iniciado_em          timestamptz not null default now(),
    terminado_em         timestamptz,
    status               text not null default 'rodando'
                         check (status in ('rodando', 'sucesso', 'falha')),
    tickets              int,
    vetores              int,
    checagens_com_falha  int,
    erro                 text  -- só o nome do erro: a URL da API carrega o token
);