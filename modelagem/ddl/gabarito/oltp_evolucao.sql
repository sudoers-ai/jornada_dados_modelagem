-- ==========================================================================
-- GABARITO - evolucao do OLTP (resposta da etapa 3)
--
-- Tente fazer sozinho primeiro, seguindo modelagem/03_evolucao_oltp/README.md.
-- Este arquivo existe para voce CONFERIR o seu trabalho, ou destravar se
-- ficou preso:   make gabarito-oltp
--
-- Pode ser aplicado mais de uma vez: todo comando e idempotente
-- (IF NOT EXISTS / OR REPLACE), e nenhum dado e apagado.
-- ==========================================================================

-- ==========================================================================
-- DEMANDA 1 - Antifraude
-- ==========================================================================

-- 1.1 O aparelho deixa de ser um texto solto e vira uma entidade
CREATE TABLE IF NOT EXISTS dispositivos (
    device_id   varchar(20) PRIMARY KEY,
    modelo      varchar(50) NOT NULL,
    sistema     varchar(20) NOT NULL,
    created_at  timestamp DEFAULT now(),
    updated_at  timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_dispositivos
    BEFORE UPDATE ON dispositivos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 1.2 A auditoria passa a guardar o aparelho, a UF e o resultado da analise
ALTER TABLE auditoria_pedidos
    ADD COLUMN IF NOT EXISTS device_id      varchar(20) REFERENCES dispositivos (device_id),
    ADD COLUMN IF NOT EXISTS uf             char(2),
    ADD COLUMN IF NOT EXISTS is_fraude      boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS motivo_fraude  varchar(30),
    ADD COLUMN IF NOT EXISTS dt_fraude      timestamp;

-- ==========================================================================
-- DEMANDA 2 - Logistica e custo de frete
-- ==========================================================================

-- 2.1 O frete e pago por peso: o produto precisa ter peso
ALTER TABLE produtos
    ADD COLUMN IF NOT EXISTS peso_gramas integer;

-- 2.2 Uma pessoa pode ter varios enderecos (e pode se mudar)
CREATE TABLE IF NOT EXISTS enderecos (
    id            serial PRIMARY KEY,
    id_pessoa     bigint NOT NULL REFERENCES pessoas (id),
    logradouro    varchar(255) NOT NULL,
    cidade        varchar(100) NOT NULL,
    uf            char(2) NOT NULL,
    cep           varchar(9) NOT NULL,
    is_principal  boolean NOT NULL DEFAULT true,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_enderecos
    BEFORE UPDATE ON enderecos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2.3 O pedido passa a saber para onde vai
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS id_endereco_entrega integer REFERENCES enderecos (id);

-- 2.4 Quem transporta
CREATE TABLE IF NOT EXISTS transportadoras (
    id            serial PRIMARY KEY,
    nome          varchar(100) NOT NULL,
    cnpj          varchar(18) NOT NULL UNIQUE,
    custo_por_kg  numeric(10,2) NOT NULL,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_transportadoras
    BEFORE UPDATE ON transportadoras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2.5 O caminhao: uma viagem de uma transportadora
CREATE TABLE IF NOT EXISTS transportes (
    id                   serial PRIMARY KEY,
    id_transportadora    integer NOT NULL REFERENCES transportadoras (id),
    placa                varchar(8) NOT NULL,
    peso_total_gramas    integer NOT NULL DEFAULT 0,
    valor_frete          numeric(10,2) NOT NULL DEFAULT 0,
    dt_saida             timestamp NOT NULL,
    dt_entrega_prevista  timestamp NOT NULL,
    dt_entrega           timestamp,
    created_at           timestamp DEFAULT now(),
    updated_at           timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_transportes
    BEFORE UPDATE ON transportes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2.6 Um caminhao leva varios pedidos: relacionamento N:N
CREATE TABLE IF NOT EXISTS carga_pedidos (
    id_transporte  integer NOT NULL REFERENCES transportes (id),
    id_pedido      integer NOT NULL REFERENCES pedidos (id),
    created_at     timestamp DEFAULT now(),
    updated_at     timestamp DEFAULT now(),
    PRIMARY KEY (id_transporte, id_pedido)
);

CREATE OR REPLACE TRIGGER set_updated_at_carga_pedidos
    BEFORE UPDATE ON carga_pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================================================
-- DEMANDA 3 - Ciclo de vida do pedido
-- ==========================================================================

-- 3.1 A situacao ATUAL do pedido
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'criado';

-- 3.2 O HISTORICO de situacoes: um evento por linha
CREATE TABLE IF NOT EXISTS status_pedidos (
    id_pedido   integer NOT NULL REFERENCES pedidos (id),
    status      varchar(20) NOT NULL,
    dt_evento   timestamp NOT NULL,
    created_at  timestamp DEFAULT now(),
    updated_at  timestamp DEFAULT now(),
    PRIMARY KEY (id_pedido, status)
);

CREATE OR REPLACE TRIGGER set_updated_at_status_pedidos
    BEFORE UPDATE ON status_pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3.3 Como o pedido foi pago
CREATE TABLE IF NOT EXISTS pagamentos (
    id            serial PRIMARY KEY,
    id_pedido     integer NOT NULL REFERENCES pedidos (id),
    forma         varchar(20) NOT NULL,
    parcelas      integer NOT NULL DEFAULT 1,
    valor         numeric(10,2) NOT NULL,
    status        varchar(20) NOT NULL DEFAULT 'pendente',
    dt_pagamento  timestamp,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_pagamentos
    BEFORE UPDATE ON pagamentos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================================================
-- Rede de seguranca do gabarito: se voce criou alguma coluna a mao SEM a
-- chave estrangeira, os comandos acima nao a recriam (a coluna ja existe).
-- Este bloco garante as FKs mesmo assim.
-- ==========================================================================
DO $$
DECLARE
    fk record;
BEGIN
    FOR fk IN
        SELECT * FROM (VALUES
            ('auditoria_pedidos', 'device_id',           'dispositivos',    'device_id'),
            ('enderecos',         'id_pessoa',           'pessoas',         'id'),
            ('pedidos',           'id_endereco_entrega', 'enderecos',       'id'),
            ('transportes',       'id_transportadora',   'transportadoras', 'id'),
            ('carga_pedidos',     'id_transporte',       'transportes',     'id'),
            ('carga_pedidos',     'id_pedido',           'pedidos',         'id'),
            ('status_pedidos',    'id_pedido',           'pedidos',         'id'),
            ('pagamentos',        'id_pedido',           'pedidos',         'id')
        ) AS t(tabela, coluna, tabela_ref, coluna_ref)
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
            WHERE c.contype = 'f'
              AND c.conrelid = ('public.' || fk.tabela)::regclass
              AND c.confrelid = ('public.' || fk.tabela_ref)::regclass
              AND a.attname = fk.coluna
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD FOREIGN KEY (%I) REFERENCES %I (%I)',
                           fk.tabela, fk.coluna, fk.tabela_ref, fk.coluna_ref);
        END IF;
    END LOOP;
END $$;
