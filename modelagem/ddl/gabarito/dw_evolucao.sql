-- ==========================================================================
-- GABARITO - evolucao do DW (resposta da etapa 6)
--
-- Tente fazer sozinho primeiro, seguindo modelagem/05_evolucao_dw/README.md.
-- Este arquivo existe para voce CONFERIR o seu trabalho, ou destravar se
-- ficou preso:   make gabarito-dw
--
-- Pode ser aplicado mais de uma vez. O esvaziamento do legado (passo 0) so
-- acontece enquanto a fato ainda tem o formato antigo.
-- ==========================================================================

-- ==========================================================================
-- 0. O DW e DERIVADO do transacional: pode ser esvaziado e reconstruido.
--    Esvaziamos o legado para poder mudar a estrutura sem brigar com dados
--    antigos. O novo ETL recarrega tudo.
-- ==========================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'fato_pedidos'
                 AND column_name = 'total') THEN
        TRUNCATE fato_pedidos, dim_pessoas, dim_produtos RESTART IDENTITY CASCADE;
    END IF;
END $$;

-- O staging antigo sai de cena: o novo ETL usa o schema `stg`.
DROP TABLE IF EXISTS stg_pessoas, stg_produtos, stg_pedidos;

-- ==========================================================================
-- 1. Dimensoes que NAO existem no transacional
-- ==========================================================================

-- 1.1 Calendario
CREATE TABLE IF NOT EXISTS dim_tempo (
    sk_tempo       integer PRIMARY KEY,
    data           date NOT NULL UNIQUE,
    ano            integer NOT NULL,
    trimestre      integer NOT NULL,
    mes            integer NOT NULL,
    nome_mes       varchar(20) NOT NULL,
    semana_ano     integer NOT NULL,
    dia            integer NOT NULL,
    dia_semana     integer NOT NULL,
    nome_dia       varchar(20) NOT NULL,
    is_fim_semana  boolean NOT NULL,
    is_feriado     boolean NOT NULL
);

-- 1.2 Localidade (UF e regiao)
CREATE TABLE IF NOT EXISTS dim_localidade (
    sk_localidade     serial PRIMARY KEY,
    uf                char(2) NOT NULL UNIQUE,
    nome_uf           varchar(50) NOT NULL,
    regiao            varchar(20) NOT NULL,
    is_area_atendida  boolean NOT NULL
);

-- ==========================================================================
-- 2. Dimensoes que JA EXISTIAM e ganham colunas
-- ==========================================================================

-- 2.1 dim_pessoas vira SCD tipo 2
ALTER TABLE dim_pessoas
    ADD COLUMN IF NOT EXISTS id_endereco  integer,
    ADD COLUMN IF NOT EXISTS cidade       varchar(100),
    ADD COLUMN IF NOT EXISTS uf           char(2),
    ADD COLUMN IF NOT EXISTS dt_inicio    timestamp NOT NULL,
    ADD COLUMN IF NOT EXISTS dt_fim       timestamp,
    ADD COLUMN IF NOT EXISTS is_atual     boolean NOT NULL DEFAULT true;

-- 2.2 dim_produtos ganha o peso
ALTER TABLE dim_produtos
    ADD COLUMN IF NOT EXISTS peso_gramas integer;

-- ==========================================================================
-- 3. Dimensoes novas, vindas de tabelas novas do transacional
-- ==========================================================================

-- 3.1 Dispositivo (com atributos DERIVADOS)
CREATE TABLE IF NOT EXISTS dim_dispositivo (
    sk_dispositivo    serial PRIMARY KEY,
    device_id         varchar(20) NOT NULL UNIQUE,
    modelo            varchar(50) NOT NULL,
    sistema           varchar(20) NOT NULL,
    fabricante        varchar(30) NOT NULL,
    qtd_contas        integer NOT NULL DEFAULT 0,
    is_compartilhado  boolean NOT NULL DEFAULT false
);

-- 3.2 Transportadora
CREATE TABLE IF NOT EXISTS dim_transportadora (
    sk_transportadora  serial PRIMARY KEY,
    id                 integer NOT NULL UNIQUE,
    nome               varchar(100) NOT NULL,
    cnpj               varchar(18) NOT NULL,
    custo_por_kg       numeric(10,2) NOT NULL
);

-- 3.3 Forma de pagamento
CREATE TABLE IF NOT EXISTS dim_forma_pagamento (
    sk_forma_pagamento  serial PRIMARY KEY,
    forma               varchar(20) NOT NULL UNIQUE,
    descricao           varchar(50) NOT NULL,
    is_a_vista          boolean NOT NULL
);

-- ==========================================================================
-- 4. A fato que ja existia: fato_pedidos
-- ==========================================================================
ALTER TABLE fato_pedidos
    DROP COLUMN IF EXISTS dispositivo,
    DROP COLUMN IF EXISTS telefone,
    DROP COLUMN IF EXISTS total,
    ADD COLUMN IF NOT EXISTS id_produto          integer NOT NULL,
    ADD COLUMN IF NOT EXISTS sk_tempo            integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    ADD COLUMN IF NOT EXISTS sk_dispositivo      integer NOT NULL REFERENCES dim_dispositivo (sk_dispositivo),
    ADD COLUMN IF NOT EXISTS sk_localidade       integer NOT NULL REFERENCES dim_localidade (sk_localidade),
    ADD COLUMN IF NOT EXISTS sk_forma_pagamento  integer NOT NULL REFERENCES dim_forma_pagamento (sk_forma_pagamento),
    ADD COLUMN IF NOT EXISTS valor_total         numeric(10,2) NOT NULL,
    ADD COLUMN IF NOT EXISTS peso_gramas         integer NOT NULL,
    ADD COLUMN IF NOT EXISTS status              varchar(20) NOT NULL,
    ADD COLUMN IF NOT EXISTS is_fraude           boolean NOT NULL,
    ADD COLUMN IF NOT EXISTS motivo_fraude       varchar(30),
    ALTER COLUMN qtde SET NOT NULL,
    ALTER COLUMN valor_unit SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fato_pedidos_item
    ON fato_pedidos (id_pedido, id_produto);

-- ==========================================================================
-- 5. Fatos novas
-- ==========================================================================

-- 5.1 fato_entregas - grao: 1 linha por pedido embarcado em um transporte
CREATE TABLE IF NOT EXISTS fato_entregas (
    sk_id                serial PRIMARY KEY,
    id_transporte        integer NOT NULL,
    id_pedido            integer NOT NULL,
    sk_transportadora    integer NOT NULL REFERENCES dim_transportadora (sk_transportadora),
    sk_pessoa            bigint  NOT NULL REFERENCES dim_pessoas (sk_pessoa),
    sk_localidade        integer NOT NULL REFERENCES dim_localidade (sk_localidade),
    sk_tempo_saida       integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    sk_tempo_entrega     integer REFERENCES dim_tempo (sk_tempo),
    dt_saida             timestamp NOT NULL,
    dt_entrega_prevista  timestamp NOT NULL,
    dt_entrega           timestamp,
    peso_gramas          integer NOT NULL,
    valor_frete          numeric(10,2) NOT NULL,
    dias_transito        integer,
    dias_atraso          integer,
    is_entregue          boolean NOT NULL,
    is_atrasada          boolean NOT NULL,
    UNIQUE (id_transporte, id_pedido)
);

-- 5.2 fato_ciclo_pedido - snapshot acumulado, grao: 1 linha por pedido
CREATE TABLE IF NOT EXISTS fato_ciclo_pedido (
    id_pedido            integer PRIMARY KEY,
    sk_pessoa            bigint  NOT NULL REFERENCES dim_pessoas (sk_pessoa),
    sk_tempo_criado      integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    status_atual         varchar(20) NOT NULL,
    dt_criado            timestamp NOT NULL,
    dt_pago              timestamp,
    dt_separado          timestamp,
    dt_enviado           timestamp,
    dt_entregue          timestamp,
    dt_cancelado         timestamp,
    dt_devolvido         timestamp,
    horas_ate_pagamento  numeric(10,2),
    horas_ate_envio      numeric(10,2),
    horas_ate_entrega    numeric(10,2),
    valor_total          numeric(10,2) NOT NULL,
    is_fraude            boolean NOT NULL
);

-- 5.3 fato_peso_diario - snapshot periodico, grao: 1 linha por dia e transportadora
CREATE TABLE IF NOT EXISTS fato_peso_diario (
    sk_tempo           integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    sk_transportadora  integer NOT NULL REFERENCES dim_transportadora (sk_transportadora),
    qtd_transportes    integer NOT NULL,
    qtd_pedidos        integer NOT NULL,
    peso_total_gramas  bigint NOT NULL,
    valor_frete_total  numeric(12,2) NOT NULL,
    PRIMARY KEY (sk_tempo, sk_transportadora)
);
