-- ==========================================================================
-- ETL - passo 01 - STAGING: a fotografia do transacional
--
-- Aqui acontecem o "E" (Extract) e o "L" de carga bruta: copiamos as tabelas
-- do transacional para o schema `stg` do DW, SEM transformar nada.
--
-- Por que copiar antes, em vez de transformar direto de la?
--   1. O transacional esta VIVO: pedidos entram a cada segundo. Se cada
--      dimensao e cada fato lesse de la num instante diferente, as contas
--      nao fechariam. A staging e uma FOTO: todo o ETL trabalha sobre o
--      mesmo instante.
--   2. As transformacoes sao pesadas (juncoes, agregacoes). Rodando sobre a
--      copia, o ETL nao disputa recursos com quem esta vendendo.
--
-- O BEGIN/COMMIT garante a foto: dentro de uma transacao, o postgres_fdw le
-- todas as tabelas remotas no MESMO instante.
-- ==========================================================================
SET client_min_messages = warning;

BEGIN;

DROP SCHEMA IF EXISTS stg CASCADE;
CREATE SCHEMA stg;

CREATE TABLE stg.pessoas            AS SELECT * FROM oltp.pessoas;
CREATE TABLE stg.enderecos          AS SELECT * FROM oltp.enderecos;
CREATE TABLE stg.categorias         AS SELECT * FROM oltp.categorias;
CREATE TABLE stg.produtos           AS SELECT * FROM oltp.produtos;
CREATE TABLE stg.dispositivos       AS SELECT * FROM oltp.dispositivos;
CREATE TABLE stg.transportadoras    AS SELECT * FROM oltp.transportadoras;
CREATE TABLE stg.pedidos            AS SELECT * FROM oltp.pedidos;
CREATE TABLE stg.itens_pedidos      AS SELECT * FROM oltp.itens_pedidos;
CREATE TABLE stg.auditoria_pedidos  AS SELECT * FROM oltp.auditoria_pedidos;
CREATE TABLE stg.pagamentos         AS SELECT * FROM oltp.pagamentos;
CREATE TABLE stg.status_pedidos     AS SELECT * FROM oltp.status_pedidos;
CREATE TABLE stg.transportes        AS SELECT * FROM oltp.transportes;
CREATE TABLE stg.carga_pedidos      AS SELECT * FROM oltp.carga_pedidos;

COMMIT;

-- Indices na staging: as fatos vao juntar por estas colunas milhares de vezes.
CREATE INDEX ON stg.itens_pedidos (id_pedido);
CREATE INDEX ON stg.auditoria_pedidos (id_pedido);
CREATE INDEX ON stg.pagamentos (id_pedido);
CREATE INDEX ON stg.status_pedidos (id_pedido);
CREATE INDEX ON stg.carga_pedidos (id_pedido);
ANALYZE;

\echo ''
\echo '--- prova: a fotografia (linhas copiadas por tabela)'
SELECT 'pessoas' AS tabela, count(*) AS linhas FROM stg.pessoas
UNION ALL SELECT 'enderecos',         count(*) FROM stg.enderecos
UNION ALL SELECT 'produtos',          count(*) FROM stg.produtos
UNION ALL SELECT 'dispositivos',      count(*) FROM stg.dispositivos
UNION ALL SELECT 'pedidos',           count(*) FROM stg.pedidos
UNION ALL SELECT 'itens_pedidos',     count(*) FROM stg.itens_pedidos
UNION ALL SELECT 'auditoria_pedidos', count(*) FROM stg.auditoria_pedidos
UNION ALL SELECT 'pagamentos',        count(*) FROM stg.pagamentos
UNION ALL SELECT 'status_pedidos',    count(*) FROM stg.status_pedidos
UNION ALL SELECT 'transportes',       count(*) FROM stg.transportes
UNION ALL SELECT 'carga_pedidos',     count(*) FROM stg.carga_pedidos;
