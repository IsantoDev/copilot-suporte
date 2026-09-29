-- Um embedding por ticket, gerado a partir de limpo_problemas.texto.
create extension if not exists vector;

create table if not exists vetores_problemas (
    ticket_id   integer primary key,
    modelo      text not null,
    texto_hash  text not null,
    embedding   vector(768) not null,
    gerado_em   timestamptz not null default now()
);

create index if not exists vetores_problemas_hnsw
    on vetores_problemas using hnsw (embedding vector_cosine_ops);