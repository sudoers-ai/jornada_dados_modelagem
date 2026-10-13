-- ==========================================================================
-- Liga Sudoers - banco DIMENSIONAL (DW) - modelagem LEGADA
--
-- O star schema que a empresa usa hoje (o mesmo do repo liga_sudoers):
-- 2 dimensoes, 1 fato e 3 tabelas de staging.
--
-- Este arquivo roda SOZINHO na primeira vez que o container sobe.
-- VOCE NAO EDITA ESTE ARQUIVO. A evolucao do DW e feita por voce, no banco,
-- seguindo modelagem/05_evolucao_dw/README.md.
-- ==========================================================================

CREATE TABLE public.dim_produtos (
    sk_produto  serial PRIMARY KEY,
    id          integer NOT NULL,
    cat_desc    varchar(255),
    descricao   varchar(255),
    created_at  timestamp,
    updated_at  timestamp
);

CREATE TABLE public.dim_pessoas (
    sk_pessoa   serial PRIMARY KEY,
    id          bigint NOT NULL,
    nome        varchar(255),
    sexo        varchar(1),
    dt_nasc     date,
    created_at  timestamp,
    updated_at  timestamp
);

CREATE TABLE public.stg_pessoas (
    id          bigint NOT NULL,
    nome        varchar(255),
    sexo        varchar(1),
    dt_nasc     date,
    created_at  timestamp,
    updated_at  timestamp
);

CREATE TABLE public.stg_produtos (
    id          integer NOT NULL,
    cat_desc    varchar(255) NOT NULL,
    descricao   varchar(255) NOT NULL,
    created_at  timestamp DEFAULT now(),
    updated_at  timestamp DEFAULT now()
);

CREATE TABLE public.stg_pedidos (
    id_pedido    integer NOT NULL,
    id_pessoa    bigint NOT NULL,
    id_produto   integer NOT NULL,
    dispositivo  varchar(50) NOT NULL,
    geohash      varchar(50) NOT NULL,
    telefone     varchar(20) NOT NULL,
    dt_venda     timestamp NOT NULL,
    qtde         integer NOT NULL,
    valor_unit   numeric(10,2) NOT NULL,
    valor_total  numeric(10,2) NOT NULL
);

CREATE TABLE public.fato_pedidos (
    sk_id        serial PRIMARY KEY,
    id_pedido    integer NOT NULL,
    sk_pessoa    bigint NOT NULL,
    sk_produto   integer NOT NULL,
    dispositivo  varchar(50) NOT NULL,
    geohash      varchar(50) NOT NULL,
    telefone     varchar(20) NOT NULL,
    dt_venda     timestamp NOT NULL,
    qtde         integer,
    valor_unit   numeric(10,2),
    total        numeric(10,2),
    CONSTRAINT fk_pessoa  FOREIGN KEY (sk_pessoa)  REFERENCES public.dim_pessoas (sk_pessoa),
    CONSTRAINT fk_produto FOREIGN KEY (sk_produto) REFERENCES public.dim_produtos (sk_produto)
);
